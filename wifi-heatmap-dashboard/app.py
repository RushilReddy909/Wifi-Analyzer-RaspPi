from flask import Flask, render_template, jsonify, Response, request
from analyzer import (
    generate_heatmap, 
    generate_time_series_trends,
    analyze_channel_overlap,
    get_network_statistics,
    generate_interactive_heatmap,
    generate_interactive_trends,
    load_all_data
)
from alerts import AlertSystem, run_alert_checks
import json
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# Enhanced cache with timestamps
cache = {
    'static_dashboard': {'timestamp': None, 'data': None},
    'interactive_dashboard': {'timestamp': None, 'data': None},
    'stats': {'timestamp': None, 'data': None}
}

# Cache duration in seconds
CACHE_DURATION = 60  # 1 minute

# Initialize alert system
alert_system = AlertSystem()

def is_cache_valid(cache_key):
    """Check if cache is still valid"""
    if cache[cache_key]['timestamp'] is None:
        return False
    age = (datetime.now() - cache[cache_key]['timestamp']).total_seconds()
    return age < CACHE_DURATION

@app.route("/")
def index():
    try:
        # Check cache first
        if is_cache_valid('static_dashboard'):
            print("Using cached static dashboard")
            return cache['static_dashboard']['data']
        
        print("Generating new static dashboard...")
        
        # Generate static visualizations (limit data to last 7 days for performance)
        heatmap_path, barchart_path, room_averages = generate_heatmap(hours_back=168)  # 7 days
        trends_path = generate_time_series_trends(hours_back=24)
        channel_path, channel_recs = analyze_channel_overlap(hours_back=168)  # 7 days
        
        stats = get_network_statistics(hours_back=168)  # 7 days

        result = render_template(
            "index.html",
            heatmap=str(heatmap_path),
            barchart=str(barchart_path),
            trends=str(trends_path) if trends_path else None,
            channel=str(channel_path) if channel_path else None,
            averages=room_averages,
            channel_recs=channel_recs,
            stats=stats
        )
        
        # Cache the result
        cache['static_dashboard']['data'] = result
        cache['static_dashboard']['timestamp'] = datetime.now()
        
        return result
    except Exception as e:
        return f"<h2>Error generating dashboard</h2><p>{str(e)}</p><pre>{repr(e)}</pre>"


@app.route("/interactive")
def interactive_view():
    """Interactive dashboard with Plotly charts"""
    try:
        # Check cache first
        if is_cache_valid('interactive_dashboard'):
            print("Using cached interactive dashboard")
            return cache['interactive_dashboard']['data']
        
        print("Generating new interactive dashboard...")
        
        heatmap_html = generate_interactive_heatmap(hours_back=168)  # 7 days
        trends_html = generate_interactive_trends(hours_back=24)
        stats = get_network_statistics(hours_back=168)  # 7 days
        channel_path, channel_recs = analyze_channel_overlap(hours_back=168)  # 7 days
        
        result = render_template(
            "interactive.html",
            heatmap_html=heatmap_html,
            trends_html=trends_html,
            stats=stats,
            channel=str(channel_path) if channel_path else None,
            channel_recs=channel_recs
        )
        
        # Cache the result
        cache['interactive_dashboard']['data'] = result
        cache['interactive_dashboard']['timestamp'] = datetime.now()
        
        return result
    except Exception as e:
        return f"<h2>Error generating interactive dashboard</h2><p>{str(e)}</p>"


@app.route("/api/stats")
def api_stats():
    """API endpoint for statistics"""
    try:
        # Check cache first
        if is_cache_valid('stats'):
            return jsonify(cache['stats']['data'])
        
        stats = get_network_statistics(hours_back=168)  # 7 days
        
        # Cache the result
        cache['stats']['data'] = stats
        cache['stats']['timestamp'] = datetime.now()
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear_cache", methods=["POST"])
def clear_cache():
    """Clear all caches and force regeneration"""
    cache['static_dashboard'] = {'timestamp': None, 'data': None}
    cache['interactive_dashboard'] = {'timestamp': None, 'data': None}
    cache['stats'] = {'timestamp': None, 'data': None}
    return jsonify({"success": True, "message": "Cache cleared"})


@app.route("/api/latest")
def api_latest():
    """API endpoint for latest scan data"""
    try:
        df = load_all_data(hours_back=1)
        latest = df.tail(50).to_dict('records')
        
        # Convert timestamps to strings
        for record in latest:
            if 'timestamp' in record:
                record['timestamp'] = record['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify(latest)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stream")
def stream():
    """Server-Sent Events endpoint for real-time updates"""
    def event_stream():
        last_count = 0
        while True:
            try:
                df = load_all_data(hours_back=1)
                current_count = len(df)
                
                if current_count != last_count:
                    latest_data = df.tail(1).to_dict('records')[0]
                    latest_data['timestamp'] = latest_data['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                    
                    yield f"data: {json.dumps(latest_data)}\n\n"
                    last_count = current_count
                
                time.sleep(5)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(5)
    
    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/channel_recommendations")
def api_channel_recommendations():
    """API endpoint for channel recommendations"""
    try:
        _, recommendations = analyze_channel_overlap()
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts")
def api_alerts():
    """API endpoint for alerts"""
    try:
        hours = request.args.get('hours', 24, type=int)
        alerts = alert_system.get_recent_alerts(hours=hours)
        return jsonify({"alerts": alerts, "count": len(alerts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts/check")
def api_check_alerts():
    """API endpoint to trigger alert checks"""
    try:
        new_alerts = alert_system.check_all()
        return jsonify({"new_alerts": new_alerts, "count": len(new_alerts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/alerts")
def alerts_page():
    """Alerts dashboard page"""
    try:
        alerts = alert_system.get_recent_alerts(hours=24)
        return render_template("alerts.html", alerts=alerts)
    except Exception as e:
        return f"<h2>Error loading alerts</h2><p>{str(e)}</p>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
