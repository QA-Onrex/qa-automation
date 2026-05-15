# scripts/generate_dashboard.py
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

RESULTS_FILE = "data/results.json"
DASHBOARD_DATA_FILE = "docs/dashboard_data.json"


def normalize_environment(record):
    """Normalize environment field using profile as fallback"""
    environment = record.get("environment")

    # If environment exists and contains expected patterns, keep it
    if environment and ("intdev" in environment.lower() or "intacc" in environment.lower()):
        return environment

    # Fallback to profile
    profile = record.get("profile", "").lower()

    # Development patterns
    if "intdev" in profile or "dev" in profile:
        return "intdev"

    # Everything else defaults to Acceptance
    return "intacc"


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


def organize_sessions_by_environment(sessions):
    """
    Organize sessions by environment and return structured data.
    Structure:
    {
        "Development": [dev_sessions sorted by time desc],
        "Acceptance": [acc_sessions sorted by time desc],
        "All": "Development" or "Acceptance" (reference to latest environment)
    }
    """
    dev_sessions = [s for s in sessions if "intdev" in s.get("environment", "").lower()]
    acc_sessions = [s for s in sessions if "intacc" in s.get("environment", "").lower()]

    # Sort each by end time descending (newest first)
    dev_sessions.sort(key=lambda x: x.get("end", ""), reverse=True)
    acc_sessions.sort(key=lambda x: x.get("end", ""), reverse=True)

    # Determine which environment has the latest run overall
    latest_env = "Development"
    if dev_sessions and acc_sessions:
        # Both have runs, compare the latest from each
        dev_latest_time = dev_sessions[0].get("end", "")
        acc_latest_time = acc_sessions[0].get("end", "")
        if acc_latest_time > dev_latest_time:
            latest_env = "Acceptance"
    elif not dev_sessions:
        # Only acceptance has runs
        latest_env = "Acceptance"
    # else: only development has runs, keep default "Development"

    return {
        "Development": dev_sessions,
        "Acceptance": acc_sessions,
        "All": latest_env  # Reference to the environment with the latest run
    }


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
            # Normalize environment before processing
            r["environment"] = normalize_environment(r)

            project = r.get("project", "Unknown")
            suite = r.get("test_suite_id", "Unknown")
            start = r.get("start") or r.get("end")
            if not start:
                continue

            # Parse date safely
            try:
                start_str = start.replace("Z", "+00:00")
                # Extract just the date from the ISO string (YYYY-MM-DD part)
                date_only = start_str.split("T")[0]  # Get "2026-05-15" from "2026-05-15T00:02:23.8+02:00"
                # Convert to dashboard format: "2026.05.15"
                date = date_only.replace("-", ".")
                all_dates_set.add(date)
            except (ValueError, IndexError):
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
                    # Organize sessions by environment (no data duplication)
                    sessions_by_env = organize_sessions_by_environment(sessions)

                    data_dict[project][suite][date] = {
                        "sessions": sessions_by_env
                    }

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