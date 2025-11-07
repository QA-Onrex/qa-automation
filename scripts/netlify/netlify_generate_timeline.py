# scripts/netlify/netlify_generate_timeline.py
import os
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict

DASHBOARD_DATA_FILE = "docs/dashboard_data.json"
TIMELINE_FILE = "docs/timeline_data.json" 
TIME_WINDOW_DAYS = 5

def load_json_data(filepath):
    """Safely loads and returns JSON data from a file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {filepath} is empty or invalid. Starting fresh.")
            return {}
    return {}

def save_json_data(filepath, data):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_environment(environment_field):
    """Extract environment from environment field."""
    if not environment_field:
        return None
    
    environment_lower = str(environment_field).lower()
    if "intdev" in environment_lower:
        return "intdev"
    elif "intacc" in environment_lower:
        return "intacc"
    else:
        return None

def generate_timeline():
    """Generates the timeline data structure from dashboard data."""
    # 1. Load dashboard data
    dashboard_data = load_json_data(DASHBOARD_DATA_FILE)
    
    if not dashboard_data or 'data' not in dashboard_data:
        print("No dashboard data found. Skipping timeline generation.")
        return

    # 2. Initialize timeline structure using defaultdict
    timeline_data = defaultdict(lambda: {
        "ALL": {"total": 0, "passed": 0, "failed": 0},
        "intdev": {"total": 0, "passed": 0, "failed": 0},
        "intacc": {"total": 0, "passed": 0, "failed": 0}
    })
    
    # 3. Process all projects, suites, and dates
    for project, suites in dashboard_data['data'].items():
        for suite, dates in suites.items():
            for date_str, date_data in dates.items():
                # Convert date string to datetime object for filtering
                try:
                    date_obj = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                
                # Skip if date is older than TIME_WINDOW_DAYS
                cutoff_dt = datetime.now(timezone.utc) - timedelta(days=TIME_WINDOW_DAYS)
                if date_obj < cutoff_dt:
                    continue
                
                # Process sessions for this date
                for session in date_data.get("sessions", []):
                    start_time_str = session.get("start")
                    if not start_time_str:
                        continue
                        
                    try:
                        # Parse start time
                        if '+' in start_time_str or '-' in start_time_str:
                            start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                        else:
                            start_dt = datetime.strptime(start_time_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)

                        # Convert to UTC and get hour start
                        start_dt_utc = start_dt.astimezone(timezone.utc)
                        hour_start_dt = start_dt_utc.replace(minute=0, second=0, microsecond=0)
                        hour_key = hour_start_dt.isoformat().replace('+00:00', 'Z')
                        
                        # Extract environment from environment field
                        environment_field = session.get("environment", "")
                        environment = extract_environment(environment_field)
                        
                        # Skip if environment is not intdev or intacc
                        if environment is None:
                            continue
                        
                        # Get test case counts
                        test_cases = session.get("test_cases", 0)
                        passed = session.get("passed", 0)
                        failed = session.get("failed", 0)
                        
                        # Update ALL environment
                        timeline_data[hour_key]["ALL"]["total"] += test_cases
                        timeline_data[hour_key]["ALL"]["passed"] += passed
                        timeline_data[hour_key]["ALL"]["failed"] += failed
                        
                        # Update specific environment
                        timeline_data[hour_key][environment]["total"] += test_cases
                        timeline_data[hour_key][environment]["passed"] += passed
                        timeline_data[hour_key][environment]["failed"] += failed
                        
                    except Exception as e:
                        print(f"Error processing session: {e}")
                        continue

    # 4. Convert defaultdict to regular dict and sort by timestamp
    sorted_timeline_data = dict(sorted(timeline_data.items()))
    
    # 5. Additional pruning for any remaining old data (based on hour_key)
    utc_now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    cutoff_dt = utc_now - timedelta(days=TIME_WINDOW_DAYS)
    
    keys_to_remove = []
    for hour_key in sorted_timeline_data.keys():
        try:
            hour_dt = datetime.fromisoformat(hour_key.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            if hour_dt < cutoff_dt:
                keys_to_remove.append(hour_key)
        except:
            keys_to_remove.append(hour_key)
    
    for key in keys_to_remove:
        del sorted_timeline_data[key]
        print(f"Pruned old data: {key}")

    # 6. Save timeline data
    save_json_data(TIMELINE_FILE, sorted_timeline_data)
    print(f"Successfully generated timeline data with {len(sorted_timeline_data)} hourly blocks.")
    print(f"Data covers from {min(sorted_timeline_data.keys()) if sorted_timeline_data else 'N/A'} to {max(sorted_timeline_data.keys()) if sorted_timeline_data else 'N/A'}")

if __name__ == "__main__":
    generate_timeline()
