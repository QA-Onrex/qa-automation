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

def is_test_suite_passed(session):
    """Determine if a test suite run passed (all test cases passed)."""
    failed = session.get("failed", 0)
    error = session.get("error", 0)
    incomplete = session.get("incomplete", 0)
    
    # Test suite passes only if there are no failures, errors, or incomplete tests
    return failed == 0 and error == 0 and incomplete == 0

def generate_timeline():
    """Generates the timeline data structure from dashboard data."""
    # 1. Load dashboard data
    dashboard_data = load_json_data(DASHBOARD_DATA_FILE)
    
    if not dashboard_data or 'data' not in dashboard_data:
        print("No dashboard data found. Skipping timeline generation.")
        return

    # 2. Initialize timeline structure using defaultdict
    timeline_data = defaultdict(lambda: {
        "ALL": {
            "total": 0, 
            "passed": 0, 
            "failed": 0,
            "passed_details": [],  # List of passed test suite details
            "failed_details": []   # List of failed test suite details
        },
        "intdev": {
            "total": 0, 
            "passed": 0, 
            "failed": 0,
            "passed_details": [],
            "failed_details": []
        },
        "intacc": {
            "total": 0, 
            "passed": 0, 
            "failed": 0,
            "passed_details": [],
            "failed_details": []
        }
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
                        
                        # Get test suite name (extract the last part for brevity)
                        test_suite_id = session.get("test_suite_id", "")
                        # Extract just the last part of the test suite path for display
                        test_suite_name = test_suite_id.split('/')[-1] if test_suite_id else "Unknown Suite"
                        
                        # Create test suite detail object
                        suite_detail = {
                            "name": test_suite_name,
                            "start_time": start_dt_utc.isoformat().replace('+00:00', 'Z'),
                            "full_name": test_suite_id,
                            "test_cases": session.get("test_cases", 0),
                            "passed_cases": session.get("passed", 0),
                            "failed_cases": session.get("failed", 0),
                            "error_cases": session.get("error", 0),
                            "project": project
                        }
                        
                        # Determine if test suite passed or failed
                        passed = is_test_suite_passed(session)
                        
                        # Update ALL environment - count test suite as 1
                        timeline_data[hour_key]["ALL"]["total"] += 1
                        if passed:
                            timeline_data[hour_key]["ALL"]["passed"] += 1
                            timeline_data[hour_key]["ALL"]["passed_details"].append(suite_detail)
                        else:
                            timeline_data[hour_key]["ALL"]["failed"] += 1
                            timeline_data[hour_key]["ALL"]["failed_details"].append(suite_detail)
                        
                        # Update specific environment - count test suite as 1
                        timeline_data[hour_key][environment]["total"] += 1
                        if passed:
                            timeline_data[hour_key][environment]["passed"] += 1
                            timeline_data[hour_key][environment]["passed_details"].append(suite_detail)
                        else:
                            timeline_data[hour_key][environment]["failed"] += 1
                            timeline_data[hour_key][environment]["failed_details"].append(suite_detail)
                        
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
    
    # Print some statistics
    total_suites = sum(hour_data["ALL"]["total"] for hour_data in sorted_timeline_data.values())
    total_passed = sum(hour_data["ALL"]["passed"] for hour_data in sorted_timeline_data.values())
    total_failed = sum(hour_data["ALL"]["failed"] for hour_data in sorted_timeline_data.values())
    print(f"Total test suite runs: {total_suites} (Passed: {total_passed}, Failed: {total_failed})")
    
    # Print sample of detailed data
    if sorted_timeline_data:
        sample_hour = next(iter(sorted_timeline_data.values()))
        sample_passed_count = len(sample_hour["ALL"]["passed_details"])
        sample_failed_count = len(sample_hour["ALL"]["failed_details"])
        print(f"Sample hour contains: {sample_passed_count} passed suites, {sample_failed_count} failed suites with details")

if __name__ == "__main__":
    generate_timeline()
