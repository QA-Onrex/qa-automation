# scripts/netlify/netlify_generate_timeline.py
import os
import json
from datetime import datetime, timedelta, timezone

DASHBOARD_DATA_FILE = "docs/dashboard_data.json"
TIMELINE_FILE = "docs/timeline_data.json" 
TIME_WINDOW_DAYS = 5
MAX_SESSIONS_PER_HOUR = 20

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

def get_session_status(session):
    """Determines if a session is passed or failed."""
    if session.get('sum_check', False):
        if session.get('failed', 0) == 0 and session.get('error', 0) == 0:
            return 'passed'
    return 'failed'

def extract_environment(profile_or_env):
    """Extract environment from profile or environment field."""
    if not profile_or_env:
        return None
    
    profile_lower = str(profile_or_env).lower()
    if "intdev" in profile_lower:
        return "intdev"
    elif "intacc" in profile_lower:
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

    # 2. Initialize timeline structure
    timeline_data = {}
    
    # 3. Process all projects, suites, and dates
    for project, suites in dashboard_data['data'].items():
        for suite, dates in suites.items():
            for date_str, date_data in dates.items():
                if 'sessions' not in date_data:
                    continue
                    
                for session in date_data['sessions']:
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
                        
                        # Extract environment from profile or environment field
                        profile = session.get("profile", "")
                        environment_field = session.get("environment", "")
                        environment = extract_environment(profile) or extract_environment(environment_field)
                        
                        # Skip if environment is not intdev or intacc
                        if environment is None:
                            continue
                        
                        # Initialize hour data if not exists
                        if hour_key not in timeline_data:
                            timeline_data[hour_key] = {
                                "ALL": {"total": 0, "passed": 0, "failed": 0},
                                "intdev": {"total": 0, "passed": 0, "failed": 0},
                                "intacc": {"total": 0, "passed": 0, "failed": 0}
                            }
                        
                        # Determine status and update counts
                        status = get_session_status(session)
                        
                        # Update ALL environment
                        timeline_data[hour_key]["ALL"]["total"] += 1
                        timeline_data[hour_key]["ALL"][status] += 1
                        
                        # Update specific environment
                        timeline_data[hour_key][environment]["total"] += 1
                        timeline_data[hour_key][environment][status] += 1
                        
                    except Exception as e:
                        print(f"Error processing session: {e}")
                        continue

    # 4. Prune data older than 5 days
    utc_now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    cutoff_dt = utc_now - timedelta(days=TIME_WINDOW_DAYS)
    
    keys_to_remove = []
    for hour_key in timeline_data.keys():
        try:
            hour_dt = datetime.fromisoformat(hour_key.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            if hour_dt < cutoff_dt:
                keys_to_remove.append(hour_key)
        except:
            keys_to_remove.append(hour_key)
    
    for key in keys_to_remove:
        del timeline_data[key]
        print(f"Pruned old data: {key}")

    # 5. Save timeline data
    save_json_data(TIMELINE_FILE, timeline_data)
    print(f"Successfully generated timeline data with {len(timeline_data)} hourly blocks.")
    print(f"Data covers from {min(timeline_data.keys()) if timeline_data else 'N/A'} to {max(timeline_data.keys()) if timeline_data else 'N/A'}")

if __name__ == "__main__":
    generate_timeline()
