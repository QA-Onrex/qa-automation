# scripts/netlify/netlify_dashboard_data.py
import json
import os
import hashlib
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/netlify_results.json"
DASHBOARD_DATA_FILE = "docs/dashboard_data.json"

def load_results():
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found.")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_color(record):
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    failed = record.get("failed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

    total_calc = passed + failed + errored + incomplete + skipped
    if total_calc != total:
        return "red"

    if passed == total:
        return "yellow" if retry > 0 else "green"

    return "red"

def generate_dashboard_data():
    results = load_results()
    if not results:
        print("No results found.")
        return

    # Group data by Project → Test Suite ID → Date
    data = defaultdict(lambda: defaultdict(dict))
    all_dates_set = set()

    for r in results:
        project = r.get("project", "Unknown")
        suite = r.get("test_suite_id", "Unknown")
        start = r.get("start") or r.get("end")
        if not start:
            continue
            
        # Use strptime for robust ISO 8601 parsing with timezone info
        try:
            start_str = start.replace("Z", "+00:00")
            if "." in start_str:
                dt_obj = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                dt_obj = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S%z")

            date = dt_obj.strftime("%Y.%m.%d")
            all_dates_set.add(date)
        except ValueError:
            continue

        # Keep only latest record for the date
        if date not in data[project][suite] or r.get("end", "") > data[project][suite][date].get("end", ""):
            r["color"] = get_color(r)
            data[project][suite][date] = r

    # Convert defaultdict to regular dict for JSON serialization
    data_dict = {}
    for project in data:
        data_dict[project] = {}
        for suite in data[project]:
            data_dict[project][suite] = dict(data[project][suite])

    # Prepare dashboard data
    dashboard_data = {
        "data": data_dict,
        "dates": sorted(all_dates_set, reverse=True)[:365],
        "last_updated": datetime.now().isoformat()
    }

    # Write to dashboard data file
    os.makedirs(os.path.dirname(DASHBOARD_DATA_FILE), exist_ok=True)
    with open(DASHBOARD_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2, default=str)

    print(f"✅ Dashboard data updated successfully: {DASHBOARD_DATA_FILE}")
    print(f"   - Projects: {len(data_dict)}")
    print(f"   - Dates range: {len(dashboard_data['dates'])} days")
    print(f"   - Last updated: {dashboard_data['last_updated']}")

if __name__ == "__main__":
    generate_dashboard_data()
