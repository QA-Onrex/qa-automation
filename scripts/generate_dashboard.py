# scripts/generate_dashboard.py
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

RESULTS_FILE = "data/results.json"
DASHBOARD_DATA_FILE = "docs/dashboard_data.json"


def load_results():
    """Load test results from JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def deduplicate_results(results):
    """Remove duplicate entries by html_filename or netlify_url (keep latest)."""
    seen = {}
    for r in results:
        key = r.get("html_filename") or r.get("netlify_url")
        if key:
            seen[key] = r
    return list(seen.values())


def generate_dashboard_data():
    """Generate clean dashboard data from test results"""
    try:
        results = load_results()
        if not results:
            # GitHub Actions annotation (match style used in other scripts)
            print("No results found.")
            print("::notice::⏭️ Results found: 0")
            return

        # Deduplicate before processing
        results = deduplicate_results(results)

        # Group data by Project → Test Suite ID → Date
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        all_dates_set = set()
        total_reports_count = 0

        print("Processing test results...")

        for r in results:
            project = r.get("project", "Unknown")
            suite = r.get("test_suite_id", "Unknown")
            start = r.get("start") or r.get("end")
            if not start:
                continue

            # Parse date safely
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

            # Store session
            data[project][suite][date].append(r)
            total_reports_count += 1

            # Sort newest first
            data[project][suite][date].sort(key=lambda x: x.get("end", ""), reverse=True)

        # Build frontend-friendly data
        data_dict = {}
        for project in data:
            data_dict[project] = {}
            for suite in data[project]:
                data_dict[project][suite] = {}
                for date, sessions in data[project][suite].items():
                    # --- START MODIFICATION ---
                    # 1. Calculate session count
                    session_count = len(sessions)
                    
                    # 2. Create a copy of the latest session and augment it with the count
                    latest_session = sessions[0].copy()
                    latest_session["sessionCount"] = session_count

                    data_dict[project][suite][date] = {
                        "sessions": sessions,
                        "latest": latest_session  # Use the augmented session object
                    }
                    # --- END MODIFICATION ---

        dashboard_data = {
            "data": data_dict,
            "dates": sorted(all_dates_set, reverse=True)[:365],
            "last_updated": (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y, %H:%M:%S (GMT+1)")
        }

        # Ensure output folder exists
        os.makedirs(os.path.dirname(DASHBOARD_DATA_FILE), exist_ok=True)

        with open(DASHBOARD_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2, default=str)

        print(f"📊 Reports processed: {total_reports_count}")
        # GitHub Actions annotation summary
        print(f"::notice::📊 Results found: {len(results)}")
        print(f"::notice::✅ Reports processed: {total_reports_count}")
        print(f"Dashboard data updated: {DASHBOARD_DATA_FILE}")
        print(f"Projects: {len(data_dict)}")
        print(f"Last updated: {dashboard_data['last_updated']}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_dashboard_data()
