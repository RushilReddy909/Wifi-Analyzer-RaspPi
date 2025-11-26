#!/usr/bin/env python3
"""
Database Maintenance Script
Manage, cleanup, and optimize the WiFi analyzer database
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "data" / "wifi_data.db"

def get_stats():
    """Get database statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM wifi_scans")
    total_records = cursor.fetchone()[0]
    
    # Date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM wifi_scans")
    min_date, max_date = cursor.fetchone()
    
    # Unique networks
    cursor.execute("SELECT COUNT(DISTINCT ssid) FROM wifi_scans")
    unique_networks = cursor.fetchone()[0]
    
    # Unique rooms
    cursor.execute("SELECT COUNT(DISTINCT room) FROM wifi_scans")
    unique_rooms = cursor.fetchone()[0]
    
    # Database size
    db_size = DB_PATH.stat().st_size / (1024 * 1024)  # MB
    
    conn.close()
    
    print("=" * 50)
    print("📊 Database Statistics")
    print("=" * 50)
    print(f"Total Records:     {total_records:,}")
    print(f"Unique Networks:   {unique_networks}")
    print(f"Unique Rooms:      {unique_rooms}")
    print(f"Date Range:        {min_date} to {max_date}")
    print(f"Database Size:     {db_size:.2f} MB")
    print("=" * 50)


def cleanup_old_data(days):
    """Remove data older than specified days"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    # Count records to delete
    cursor.execute("SELECT COUNT(*) FROM wifi_scans WHERE timestamp < ?", (cutoff_date,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"✅ No records older than {days} days found")
        conn.close()
        return
    
    print(f"🗑️  Found {count:,} records older than {days} days")
    confirm = input("Delete these records? (yes/no): ")
    
    if confirm.lower() == 'yes':
        cursor.execute("DELETE FROM wifi_scans WHERE timestamp < ?", (cutoff_date,))
        conn.commit()
        print(f"✅ Deleted {count:,} old records")
        
        # Vacuum to reclaim space
        print("🔧 Optimizing database...")
        cursor.execute("VACUUM")
        print("✅ Database optimized")
    else:
        print("❌ Cleanup cancelled")
    
    conn.close()


def export_to_csv(output_file, days=None):
    """Export database to CSV"""
    conn = sqlite3.connect(DB_PATH)
    
    if days:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        query = "SELECT * FROM wifi_scans WHERE timestamp >= ? ORDER BY timestamp"
        cursor = conn.execute(query, (cutoff_date,))
    else:
        query = "SELECT * FROM wifi_scans ORDER BY timestamp"
        cursor = conn.execute(query)
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Write to CSV
    with open(output_file, 'w') as f:
        f.write(','.join(columns) + '\n')
        
        count = 0
        for row in cursor:
            f.write(','.join(str(x) if x is not None else '' for x in row) + '\n')
            count += 1
    
    conn.close()
    
    print(f"✅ Exported {count:,} records to {output_file}")


def import_from_csv(csv_file):
    """Import CSV data into database"""
    import csv
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    count = 0
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            cursor.execute("""
                INSERT INTO wifi_scans (timestamp, room, ssid, bssid, signal, channel, frequency, security, vendor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('timestamp'),
                row.get('room'),
                row.get('ssid'),
                row.get('bssid'),
                row.get('signal'),
                row.get('channel'),
                row.get('frequency'),
                row.get('security'),
                row.get('vendor')
            ))
            count += 1
            
            if count % 1000 == 0:
                print(f"Imported {count:,} records...", end='\r')
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Imported {count:,} records from {csv_file}")


def vacuum_db():
    """Optimize and compact database"""
    print("🔧 Optimizing database...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get size before
    size_before = DB_PATH.stat().st_size / (1024 * 1024)
    
    cursor.execute("VACUUM")
    conn.commit()
    conn.close()
    
    # Get size after
    size_after = DB_PATH.stat().st_size / (1024 * 1024)
    saved = size_before - size_after
    
    print(f"✅ Database optimized")
    print(f"   Before: {size_before:.2f} MB")
    print(f"   After:  {size_after:.2f} MB")
    print(f"   Saved:  {saved:.2f} MB ({saved/size_before*100:.1f}%)")


def aggregate_old_data(days):
    """Aggregate old data to hourly averages"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"📊 Aggregating data older than {days} days to hourly averages...")
    
    # Create temporary aggregated data
    cursor.execute("""
        CREATE TEMP TABLE aggregated AS
        SELECT 
            strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
            room,
            ssid,
            bssid,
            AVG(signal) as avg_signal,
            channel,
            frequency,
            security,
            vendor
        FROM wifi_scans
        WHERE timestamp < ?
        GROUP BY hour, room, ssid, bssid
    """, (cutoff_date,))
    
    # Count original records
    cursor.execute("SELECT COUNT(*) FROM wifi_scans WHERE timestamp < ?", (cutoff_date,))
    original_count = cursor.fetchone()[0]
    
    # Count aggregated records
    cursor.execute("SELECT COUNT(*) FROM aggregated")
    aggregated_count = cursor.fetchone()[0]
    
    print(f"   Original records: {original_count:,}")
    print(f"   Aggregated records: {aggregated_count:,}")
    print(f"   Reduction: {(1 - aggregated_count/original_count)*100:.1f}%")
    
    confirm = input("Replace old data with aggregates? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete old data
        cursor.execute("DELETE FROM wifi_scans WHERE timestamp < ?", (cutoff_date,))
        
        # Insert aggregated data
        cursor.execute("""
            INSERT INTO wifi_scans (timestamp, room, ssid, bssid, signal, channel, frequency, security, vendor)
            SELECT hour, room, ssid, bssid, avg_signal, channel, frequency, security, vendor
            FROM aggregated
        """)
        
        conn.commit()
        print("✅ Old data aggregated successfully")
        
        # Optimize
        vacuum_db()
    else:
        print("❌ Aggregation cancelled")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="WiFi Analyzer Database Maintenance")
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete old data')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete data older than N days')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data to CSV')
    export_parser.add_argument('output', help='Output CSV file path')
    export_parser.add_argument('--days', type=int, help='Export only last N days')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import data from CSV')
    import_parser.add_argument('input', help='Input CSV file path')
    
    # Vacuum command
    subparsers.add_parser('vacuum', help='Optimize database')
    
    # Aggregate command
    aggregate_parser = subparsers.add_parser('aggregate', help='Aggregate old data to hourly averages')
    aggregate_parser.add_argument('--days', type=int, default=7, help='Aggregate data older than N days')
    
    args = parser.parse_args()
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        print("   Run the scanner first to create the database")
        return
    
    if args.command == 'stats':
        get_stats()
    elif args.command == 'cleanup':
        cleanup_old_data(args.days)
    elif args.command == 'export':
        export_to_csv(args.output, args.days)
    elif args.command == 'import':
        import_from_csv(args.input)
    elif args.command == 'vacuum':
        vacuum_db()
    elif args.command == 'aggregate':
        aggregate_old_data(args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
