# scripts/cleanup_data.py
import json
import os
from datetime import datetime, timedelta
from dateutil import parser  # More flexible date parsing

RESULTS_FILE = "data/results.json"
DATA_RETENTION = 35
EMAIL_RETENTION = 10

def load_results():
    """Load test results from JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results):
    """Save results back to JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def filter_old_records(results, days=DATA_RETENTION):
    """Filter out records older than specified days"""
    # Create timezone-aware cutoff date
    cutoff_date = datetime.now().astimezone() - timedelta(days=days)
    filtered_results = []
    removed_count = 0
    
    for record in results:
        start = record.get("start") or record.get("end")
        if not start:
            continue
            
        try:
            # Use dateutil.parser for more robust date parsing
            record_date = parser.isoparse(start)
                
            if record_date >= cutoff_date:
                filtered_results.append(record)
            else:
                removed_count += 1
                
        except (ValueError, TypeError) as e:
            print(f"⚠️ Could not parse date '{start}': {e}. Keeping record to be safe.")
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
        filtered_results, removed_count = filter_old_records(results, days=DATA_RETENTION)
        
        # Save filtered results
        save_results(filtered_results)
        
        print(f"🗑️ Removed {removed_count} records older than {DATA_RETENTION} days")
        print(f"📊 Total records after cleanup: {len(filtered_results)}")
        print("✅ Data cleanup completed successfully")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        raise


if __name__ == "__main__":
    cleanup_old_data()
