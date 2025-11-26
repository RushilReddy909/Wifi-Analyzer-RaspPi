import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

DATA_FOLDER = Path("data")
DB_PATH = DATA_FOLDER / "wifi_data.db"
OUTPUT_HEATMAP = Path("static/heatmap.png")
OUTPUT_BARCHART = Path("static/barchart.png")
OUTPUT_TRENDS = Path("static/trends.png")
OUTPUT_CHANNEL = Path("static/channel_overlap.png")

def load_all_data(hours_back=None):
    """Load data from SQLite database with optional time filtering"""
    if not DB_PATH.exists():
        raise ValueError(f"Database not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    
    if hours_back:
        cutoff_time = (datetime.now() - timedelta(hours=hours_back)).strftime("%Y-%m-%d %H:%M:%S")
        query = """
            SELECT timestamp, room, ssid, bssid, signal, channel, frequency, security, vendor
            FROM wifi_scans
            WHERE timestamp >= ?
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn, params=(cutoff_time,))
    else:
        query = """
            SELECT timestamp, room, ssid, bssid, signal, channel, frequency, security, vendor
            FROM wifi_scans
            ORDER BY timestamp
        """
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    if df.empty:
        raise ValueError("No data found in database")
    
    # Convert signal to numeric type first, then to dBm if needed
    df['signal'] = pd.to_numeric(df['signal'], errors='coerce').fillna(0)
    df['signal_dbm'] = df['signal'].apply(lambda x: x / 2.0 - 100.0 if x > 0 else x)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def calculate_room_averages(pivot_table: pd.DataFrame) -> dict:
    """
    Calculates the average signal strength (dBm) across all SSIDs for each room.
    Returns the results as a dictionary, sorted by average signal (highest first).
    """
    room_averages = pivot_table.mean(axis=1).sort_values(ascending=False)
    return room_averages.to_dict()


def generate_time_series_trends(hours_back=24):
    """Generate time-series trend analysis for top networks"""
    df = load_all_data(hours_back=hours_back)
    
    # Get top 5 SSIDs by frequency
    top_ssids = df['ssid'].value_counts().head(5).index
    filtered = df[df['ssid'].isin(top_ssids)]
    
    # Resample to 15-minute intervals for smoother trends
    plt.figure(figsize=(10, 6))
    
    for ssid in top_ssids:
        ssid_data = filtered[filtered['ssid'] == ssid].set_index('timestamp')
        # Resample to 15min intervals and get mean
        resampled = ssid_data['signal_dbm'].resample('15T').mean()
        plt.plot(resampled.index, resampled.values, marker='o', label=ssid, linewidth=2)
    
    plt.title(f'Signal Strength Trends (Last {hours_back} Hours)')
    plt.xlabel('Time')
    plt.ylabel('Signal Strength (dBm)')
    plt.legend(loc='best', fontsize=8)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(OUTPUT_TRENDS)
    plt.close()
    
    return OUTPUT_TRENDS


def analyze_channel_overlap(hours_back=None):
    """Analyze 2.4GHz channel overlap and congestion"""
    df = load_all_data(hours_back=hours_back)
    
    # Convert channel to numeric and filter for 2.4GHz channels (1-14)
    df['channel'] = pd.to_numeric(df['channel'], errors='coerce')
    df_24ghz = df[df['channel'].notna() & (df['channel'] >= 1) & (df['channel'] <= 14)].copy()
    
    if df_24ghz.empty:
        return None, {"message": "No 2.4GHz channel data available"}
    
    # Count networks per channel
    channel_counts = df_24ghz.groupby('channel').agg({
        'ssid': 'nunique',
        'signal_dbm': 'mean'
    }).reset_index()
    channel_counts.columns = ['channel', 'network_count', 'avg_signal']
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Channel congestion bar chart
    channels = range(1, 15)
    counts = [channel_counts[channel_counts['channel'] == ch]['network_count'].values[0] 
              if ch in channel_counts['channel'].values else 0 for ch in channels]
    
    colors = ['red' if c > 5 else 'orange' if c > 3 else 'green' for c in counts]
    ax1.bar(channels, counts, color=colors, alpha=0.7)
    ax1.set_xlabel('Channel')
    ax1.set_ylabel('Number of Networks')
    ax1.set_title('2.4GHz Channel Congestion')
    ax1.set_xticks(channels)
    ax1.grid(True, alpha=0.3)
    
    # Channel overlap visualization (channels 1-11 overlap pattern)
    overlap_matrix = []
    for ch in range(1, 12):
        overlaps = []
        for other_ch in range(1, 12):
            # Channels overlap if within 4 channels of each other
            if abs(ch - other_ch) <= 4:
                overlap_count = counts[ch-1] + counts[other_ch-1]
                overlaps.append(overlap_count if ch != other_ch else counts[ch-1])
            else:
                overlaps.append(0)
        overlap_matrix.append(overlaps)
    
    im = ax2.imshow(overlap_matrix, aspect='auto', cmap='YlOrRd')
    ax2.set_xlabel('Channel')
    ax2.set_ylabel('Channel')
    ax2.set_title('Channel Overlap Interference Map')
    ax2.set_xticks(range(11))
    ax2.set_xticklabels(range(1, 12))
    ax2.set_yticks(range(11))
    ax2.set_yticklabels(range(1, 12))
    plt.colorbar(im, ax=ax2, label='Interference Level')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_CHANNEL)
    plt.close()
    
    # Recommend best channels (1, 6, 11 are non-overlapping)
    non_overlap_channels = [1, 6, 11]
    best_channel = min(non_overlap_channels, key=lambda ch: counts[ch-1])
    
    recommendations = {
        "best_channel": int(best_channel),
        "channel_usage": {int(ch): int(counts[ch-1]) for ch in channels},
        "non_overlapping_channels": non_overlap_channels,
        "total_networks_24ghz": int(df_24ghz['ssid'].nunique())
    }
    
    return OUTPUT_CHANNEL, recommendations


def get_network_statistics(hours_back=None):
    """Get comprehensive network statistics"""
    df = load_all_data(hours_back=hours_back)
    
    stats = {
        "total_scans": len(df),
        "unique_networks": df['ssid'].nunique(),
        "unique_rooms": df['room'].nunique(),
        "date_range": {
            "start": df['timestamp'].min().strftime("%Y-%m-%d %H:%M:%S"),
            "end": df['timestamp'].max().strftime("%Y-%m-%d %H:%M:%S")
        },
        "top_networks": df['ssid'].value_counts().head(10).to_dict(),
        "security_types": df['security'].value_counts().to_dict() if 'security' in df.columns else {},
        "avg_signal_by_room": df.groupby('room')['signal_dbm'].mean().to_dict()
    }
    
    return stats


def generate_heatmap(hours_back=None):
    """Generate static heatmap visualization"""
    df = load_all_data(hours_back=hours_back)

    top_ssids = df["ssid"].value_counts().head(6).index
    filtered = df[df["ssid"].isin(top_ssids)]

    pivot = filtered.pivot_table(
        index="room",
        columns="ssid",
        values="signal_dbm",
        aggfunc="mean"
    )

    room_average_data = calculate_room_averages(pivot)

    plt.figure(figsize=(8, 5))
    plt.imshow(pivot.values, aspect="auto", cmap='RdYlGn')
    plt.xticks(range(len(pivot.columns)), list(pivot.columns), rotation=45, ha="right")
    plt.yticks(range(len(pivot.index)), list(pivot.index))
    plt.colorbar(label="Signal Strength (dBm)")
    plt.title("WiFi Signal Heatmap (Room vs Network)")
    plt.tight_layout()

    plt.savefig(OUTPUT_HEATMAP)
    plt.close()

    # -------- BAR CHART (Average signal per room) --------

    plt.figure(figsize=(6, 4))

    rooms = list(room_average_data.keys())
    values = list(room_average_data.values())

    plt.bar(rooms, values, color='steelblue')
    plt.title("Average Signal Strength Per Room")
    plt.xlabel("Room")
    plt.ylabel("Signal Strength (dBm)")
    plt.xticks(rotation=20)
    plt.tight_layout()

    plt.savefig(OUTPUT_BARCHART)
    plt.close()

    return OUTPUT_HEATMAP, OUTPUT_BARCHART, room_average_data


def generate_interactive_heatmap(hours_back=None):
    """Generate interactive Plotly heatmap"""
    df = load_all_data(hours_back=hours_back)
    
    top_ssids = df["ssid"].value_counts().head(10).index
    filtered = df[df["ssid"].isin(top_ssids)]
    
    pivot = filtered.pivot_table(
        index="room",
        columns="ssid",
        values="signal_dbm",
        aggfunc="mean"
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale='RdYlGn',
        colorbar=dict(title="Signal (dBm)"),
        hoverongaps=False,
        hovertemplate='Room: %{y}<br>Network: %{x}<br>Signal: %{z:.1f} dBm<extra></extra>'
    ))
    
    fig.update_layout(
        title='WiFi Signal Strength Heatmap',
        xaxis_title='Network SSID',
        yaxis_title='Room',
        height=500,
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='white')
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def generate_interactive_trends(hours_back=24):
    """Generate interactive time-series plot"""
    df = load_all_data(hours_back=hours_back)
    
    top_ssids = df['ssid'].value_counts().head(5).index
    filtered = df[df['ssid'].isin(top_ssids)]
    
    fig = go.Figure()
    
    for ssid in top_ssids:
        ssid_data = filtered[filtered['ssid'] == ssid]
        fig.add_trace(go.Scatter(
            x=ssid_data['timestamp'],
            y=ssid_data['signal_dbm'],
            mode='lines+markers',
            name=ssid,
            hovertemplate='%{x}<br>Signal: %{y:.1f} dBm<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Signal Strength Trends (Last {hours_back} Hours)',
        xaxis_title='Time',
        yaxis_title='Signal Strength (dBm)',
        height=500,
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='white'),
        hovermode='x unified'
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')
