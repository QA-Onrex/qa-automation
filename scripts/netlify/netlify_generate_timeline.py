# scripts/netlify/netlify_generate_timeline.py
import os
import json
from datetime import datetime, timedelta, timezone

# --- File Paths ---
# This script reads from the master results file
RESULTS_FILE = "data/netlify_results.json"
# This is the new, aggregated file for the timeline chart
TIMELINE_FILE = "docs/timeline_data.json" 

# --- Constants ---
TIME_WINDOW_DAYS = 5
MAX_SESSIONS_PER_HOUR = 20

def load_json_data(filepath):
    """Safely loads and returns JSON data from a file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {filepath} is empty or invalid. Starting fresh for this file.")
            return []
    return []

def save_json_data(filepath, data):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_session_status(session):
    """Determines if a session is passed or failed/error."""
    if session.get('sum_check', False):
        # A session is considered 'passed' for the timeline if it has 0 failed and 0 error cases.
        # This simplifies the pass/fail count for the hourly block.
        if session.get('failed', 0) == 0 and session.get('error', 0) == 0:
            return 'passed'
    return 'failed'

def generate_timeline():
    """Generates the hourly aggregated timeline data."""
    # 1. Load data
    all_results = load_json_data(RESULTS_FILE)
    
    if not all_results:
        print("No master results found. Skipping timeline generation.")
        return

    # 2. Determine time window
    # We use a naive UTC datetime to establish the cutoff for consistent pruning.
    utc_now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    cutoff_dt = utc_now - timedelta(days=TIME_WINDOW_DAYS)
    
    # 3. Aggregate results from the last 5 days
    
    # aggregation_key is: (hour_start_iso_string, environment)
    # We use a dictionary to hold the working counts before merging with existing timeline data.
    current_aggregation = {} 

    for rec in all_results:
        start_time_str = rec.get("start")
        
        # Skip records without a start time or without an environment
        if not start_time_str or not rec.get("environment"):
            continue
            
        try:
            # Parse start time, handling different formats. We assume the time is accurate.
            # We standardize to UTC for the hour key.
            if '+' in start_time_str or '-' in start_time_str:
                # Format with timezone offset: "%Y-%m-%dT%H:%M:%S.%f%z"
                start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                # Format ending in Z (UTC): "%Y-%m-%dT%H:%M:%S.%fZ"
                # Need to explicitly add UTC timezone information for comparison
                start_dt = datetime.strptime(start_time_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)

        except Exception as e:
            # print(f"Skipping record due to date parsing error: {e}")
            continue

        # Convert to UTC and get the hour start
        start_dt_utc = start_dt.astimezone(timezone.utc)
        hour_start_dt = start_dt_utc.replace(minute=0, second=0, microsecond=0)
        
        # Check if record is within the 5-day window for aggregation
        if hour_start_dt < cutoff_dt.replace(minute=0, second=0, microsecond=0):
            continue 

        # Create unique key for aggregation
        hour_key = hour_start_dt.isoformat().replace('+00:00', 'Z')
        env_key = rec.get("environment")
        
        # Use a combination of a generic 'ALL' key and the specific env key for easy aggregation.
        # This handles the 'All view' requirement naturally.
        env_specific_key = (hour_key, env_key)
        all_env_key = (hour_key, "ALL")

        for key in [env_specific_key, all_env_key]:
            if key not in current_aggregation:
                current_aggregation[key] = {
                    "hour": hour_key,
                    "environment": key[1],
                    "passed": 0,
                    "failed": 0,
                    "total": 0
                }

            # Increment counts
            status = get_session_status(rec)
            current_aggregation[key][status] += 1
            current_aggregation[key]["total"] += 1


    # 4. Prune and merge with existing timeline data
    
    # Load existing timeline data
    existing_timeline = load_json_data(TIMELINE_FILE)
    
    # Initialize a new timeline list
    new_timeline_data = []
    
    # Use a set to quickly check which hour/env keys were just updated
    updated_keys_set = set(current_aggregation.keys())
    
    # Prune old data and copy un-updated recent data
    for rec in existing_timeline:
        try:
            # Ensure the hour format is correct for comparison
            rec_hour_dt = datetime.fromisoformat(rec['hour'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
        except:
            continue # Skip malformed records
            
        # 4a. Prune: If record is older than cutoff, discard.
        if rec_hour_dt < cutoff_dt:
            continue
            
        # 4b. Copy un-updated records: If this hour was NOT processed in the current run (meaning it's an old, stable record within the 5-day window), keep it.
        # Note: We use rec['environment'] here, which might be 'ALL' or a specific URL.
        existing_key = (rec['hour'], rec['environment'])
        if existing_key not in updated_keys_set:
            new_timeline_data.append(rec)
    
    # 4c. Merge: Add all newly calculated/updated aggregation records
    for key, data in current_aggregation.items():
        # Ensure total is capped at MAX_SESSIONS_PER_HOUR for visualization scaling
        data["total_capped"] = min(data["total"], MAX_SESSIONS_PER_HOUR)
        new_timeline_data.append(data)
    
    # 5. Sort and Save (ensure data is sorted by hour)
    new_timeline_data.sort(key=lambda x: (x['hour'], x['environment']))
    
    # Save the final, aggregated, and pruned data
    save_json_data(TIMELINE_FILE, new_timeline_data)
    print(f"Successfully generated timeline data for {len(new_timeline_data)} hourly blocks.")

if __name__ == "__main__":
    generate_timeline()
