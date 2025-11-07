# scripts/netlify/netlify_generate_timeline.py
import os
import json
from datetime import datetime, timedelta, timezone

RESULTS_FILE = "data/netlify_results.json"
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

def extract_environment(profile):
    """Extract environment from profile (intdev, intacc, etc.)"""
    if not profile:
        return "unknown"
    profile_lower = profile.lower()
    if "intdev" in profile_lower:
        return "intdev"
    elif "intacc" in profile_lower:
        return "intacc"
    else:
        return None  # Return None for other environments to exclude them

def generate_timeline():
    """Generates the timeline data structure with hour keys as top-level."""
    # 1. Load data
    all_results = load_json_data(RESULTS_FILE)
    
    if not all_results:
        print("No master results found. Skipping timeline generation.")
        return

    # 2. Load existing timeline data
    existing_timeline = load_json_data(TIMELINE_FILE)
    
    # 3. Determine time window
    utc_now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    cutoff_dt = utc_now - timedelta(days=TIME_WINDOW_DAYS)
    
    # 4. Process new results
    for rec in all_results:
        start_time_str = rec.get("start")
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
            
            # Skip if outside time window
            if hour_start_dt < cutoff_dt:
                continue

            # Extract environment from profile
            profile = rec.get("profile", "")
            environment = extract_environment(profile)
            
            # Skip if environment is not intdev or intacc
            if environment is None:
                continue
            
            # Initialize hour data if not exists
            if hour_key not in existing_timeline:
                existing_timeline[hour_key] = {
                    "ALL": {"total": 0, "passed": 0, "failed": 0},
                    "intdev": {"total": 0, "passed": 0, "failed": 0},
                    "intacc": {"total": 0, "passed": 0, "failed": 0}
                }
            
            # Determine status and update counts
            status = get_session_status(rec)
            
            # Update ALL environment
            existing_timeline[hour_key]["ALL"]["total"] += 1
            existing_timeline[hour_key]["ALL"][status] += 1
            
            # Update specific environment
            existing_timeline[hour_key][environment]["total"] += 1
            existing_timeline[hour_key][environment][status] += 1
            
        except Exception as e:
            continue

    # 5. Prune old data
    keys_to_remove = []
    for hour_key in existing_timeline.keys():
        try:
            hour_dt = datetime.fromisoformat(hour_key.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            if hour_dt < cutoff_dt:
                keys_to_remove.append(hour_key)
        except:
            keys_to_remove.append(hour_key)
    
    for key in keys_to_remove:
        del existing_timeline[key]

    # 6. Save as object with hour keys
    save_json_data(TIMELINE_FILE, existing_timeline)
    print(f"Successfully generated timeline data with {len(existing_timeline)} hourly blocks.")

if __name__ == "__main__":
    generate_timeline()
