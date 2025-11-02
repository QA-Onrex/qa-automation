# scripts/netlify/netlify_data_cleanup.py
import json
import os
from datetime import datetime, timedelta

RESULTS_FILE = "data/netlify_results.json"


def load_results():
    """Load test results from JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results):
    """Save results back to JSON file"""
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def filter_old_records(results, days=35):
    """Filter out records older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_results = []
    removed_count = 0
    
    for record in results:
        start = record.get("start") or record.get("end")
        if not start:
            continue
            
        try:
            start_str = start.replace("Z", "+00:00")
            if "." in start_str:
                record_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                record_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S%z")
                
            if record_date >= cutoff_date:
                filtered_results.append(record)
            else:
                removed_count += 1
                
        except ValueError:
            # If we can't parse the date, keep the record to be safe
            filtered_results.append(record)
    
    return filtered_results, removed_count


def cleanup_old_data():
    """Main cleanup function to remove records older than 35 days"""
    try:
        print("🧹 Starting data cleanup...")
        
        # Load current results
        results = load_results()
        if not results:
            print("⏭️ No data to clean up")
            return
        
        original_count = len(results)
        print(f"📊 Total records before cleanup: {original_count}")
        
        # Filter out records older than 35 days
        filtered_results, removed_count = filter_old_records(results, days=35)
        
        # Save filtered results
        save_results(filtered_results)
        
        print(f"🗑️ Removed {removed_count} records older than 35 days")
        print(f"📊 Total records after cleanup: {len(filtered_results)}")
        print("✅ Data cleanup completed successfully")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        raise


if __name__ == "__main__":
    cleanup_old_data()
