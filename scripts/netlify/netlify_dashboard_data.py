# scripts/netlify/prepare_dashboard_data.py
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

# Define file paths based on standard project structure
RESULTS_FILE = "data/netlify_results.json"
OUTPUT_FILE = "docs/dashboard_data.json"
OUTPUT_DIR = os.path.dirname(OUTPUT_FILE)

# --- Utility Functions ---
def get_status_color(record):
    """Determines the color (status) based on test results."""
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    failed = record.get("failed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

    total_calc = passed + failed + errored + incomplete + skipped
    # Safety check: if reported total doesn't match sum of results, flag as error (red)
    if total_calc != total:
        return "red"

    # Priority 1: All passed
    if passed == total and total > 0:
        # Check for retries which usually means yellow status
        return "yellow" if retry > 0 else "green"

    # Priority 2: Any failures/errors/incompletes
    if failed > 0 or errored > 0 or incomplete > 0:
        return "red"
        
    # Default for all others (e.g., all skipped, or zero total cases)
    return "neutral" # Use neutral status if no clear fail or success.

def get_color_class(color):
    """Maps color text to a CSS class for coloring."""
    if color == "red":
        return "status-failed"
    elif color == "green":
        return "status-passed"
    elif color == "yellow":
        return "status-retried"
    return "status-neutral"

def load_results():
    """Loads and validates the raw results file."""
    if not os.path.exists(RESULTS_FILE):
        print(f"::error::Input file not found: {RESULTS_FILE}")
        return []
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"::error::Failed to decode JSON from {RESULTS_FILE}")
        return []

def prepare_matrix_data(results):
    """
    Transforms the flat list of results into the required data matrix 
    (Project -> Suite -> Date -> Latest Record) for the comparison dashboard.
    """
    # Group data by Project -> Test Suite ID -> Date
    data = defaultdict(lambda: defaultdict(dict))

    for r in results:
        # Resilience check for string-wrapped records
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except json.JSONDecodeError:
                continue

        if not isinstance(r, dict):
             continue

        project = r.get("project", "Unknown")
        # Ensure test_suite_id is present and clean it up for the key
        suite = r.get("test_suite_id")
        if not suite:
            continue
            
        start = r.get("start") or r.get("end")
        if not start:
            continue
            
        # Robust date parsing (handles different ISO 8601 formats)
        try:
            start_str = start.replace("Z", "+00:00")
            # Try parsing with milliseconds first, then without
            try:
                dt_obj = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            except ValueError:
                dt_obj = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S%z")

            date = dt_obj.strftime("%Y.%m.%d")
        except ValueError:
            # Skip record if date cannot be parsed
            continue

        # Keep only the latest record for that (Project, Suite, Date) combination
        current_record = data[project][suite].get(date)
        if current_record is None or r.get("end", "") > current_record.get("end", ""):
            r["color"] = get_status_color(r)
            r["status_class"] = get_color_class(r["color"])
            data[project][suite][date] = r

    # Collect all unique dates across all projects/suites (latest first, max 1 year)
    all_dates = sorted(
        {d for proj in data.values() for suite in proj.values() for d in suite.keys()},
        reverse=True
    )[:365]
    
    return data, all_dates

# --- Main Execution ---
def main():
    results_data = load_results()
    if not results_data:
        sys.exit(1)

    # 1. Prepare the matrix structure
    data_map, all_dates = prepare_matrix_data(results_data)
    
    # Final data structure for the frontend
    dashboard_data = {
        "data_map": data_map,
        "all_dates": all_dates
    }

    # 2. Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. Write the structured JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Use default=str to handle datetime objects if they somehow slipped through
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"✅ Successfully created dynamic dashboard data (matrix structure) at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
