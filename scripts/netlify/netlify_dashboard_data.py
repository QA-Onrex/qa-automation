# scripts/netlify/netlify_dashboard_data.py
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

RESULTS_FILE = "data/netlify_results.json"
DASHBOARD_DATA_FILE = "docs/dashboard_data.json"
ARCHIVE_FOLDER = "docs/archive"
ARCHIVE_INDEX_FILE = os.path.join(ARCHIVE_FOLDER, "archive_index.json")


def load_results():
    """Load test results from JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"Results file not found: {RESULTS_FILE}")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_results(results):
    """Save results back to JSON file"""
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def get_color(record):
    """Determine color based on test results and retry count"""
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    failed = record.get("failed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

    # Validate test case counts
    total_calc = passed + failed + errored + incomplete + skipped
    if total_calc != total:
        return "red"

    # Determine color based on results
    if passed == total:
        return "yellow" if retry > 0 else "green"

    return "red"


def filter_old_records(results, days=35):
    """Filter out records older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_results = []
    removed_count = 0
    
    for record in results:
        start = record.get("start") or record.get("end")
        if not start:
            continue
            
        try:
            start_str = start.replace("Z", "+00:00")
            if "." in start_str:
                record_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                record_date = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S%z")
                
            if record_date >= cutoff_date:
                filtered_results.append(record)
            else:
                removed_count += 1
                
        except ValueError:
            # If we can't parse the date, keep the record to be safe
            filtered_results.append(record)
    
    if removed_count > 0:
        print(f"🗑️ Removed {removed_count} records older than {days} days")
    
    return filtered_results


def create_monthly_archive(dashboard_data):
    """Create monthly archive if it's the first of the month"""
    today = datetime.now()
    
    # Only archive on the 1st of the month
    if today.day != 1:
        return
    
    archive_date = (today - timedelta(days=1)).strftime("%Y_%m")  # Previous month
    archive_file = os.path.join(ARCHIVE_FOLDER, f"{archive_date}_dashboard_data.json")
    
    # Ensure archive folder exists
    os.makedirs(ARCHIVE_FOLDER, exist_ok=True)
    
    # Validate dashboard data before archiving
    if not validate_dashboard_data(dashboard_data):
        print(f"❌ Archive validation failed for {archive_date} - skipping archive")
        return
    
    # Save archive
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2, default=str)
    
    # Update archive index
    update_archive_index(archive_date)
    
    print(f"📁 Monthly archive created: {archive_file}")


def validate_dashboard_data(dashboard_data):
    """Validate dashboard data structure"""
    try:
        required_fields = ["data", "dates", "last_updated"]
        for field in required_fields:
            if field not in dashboard_data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check if there's at least some data
        if not dashboard_data["data"]:
            print("❌ No data in dashboard")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Archive validation error: {e}")
        return False


def update_archive_index(archive_date):
    """Update the archive index with new archive date"""
    index = load_archive_index()
    
    # Add new archive date if not already present
    if archive_date not in index:
        index.append(archive_date)
        index.sort(reverse=True)  # Most recent first
        
        # Save updated index
        with open(ARCHIVE_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        
        print(f"📋 Archive index updated with: {archive_date}")


def load_archive_index():
    """Load existing archive index or create new one"""
    if os.path.exists(ARCHIVE_INDEX_FILE):
        with open(ARCHIVE_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def generate_dashboard_data():
    """Generate dashboard data from test results"""
    try:
        # Load and validate results
        results = load_results()
        if not results:
            print("⏭️ Reports processed: 0")
            return

        # Apply 35-day retention policy
        results = filter_old_records(results, days=35)
        
        if not results:
            print("⏭️ No reports after 35-day filter")
            return

        # Group data by Project → Test Suite ID → Date
        data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        all_dates_set = set()
        total_reports_count = 0

        print("Processing test results...")
        
        # Process each test result record - store ALL sessions
        for r in results:
            project = r.get("project", "Unknown")
            suite = r.get("test_suite_id", "Unknown")
            start = r.get("start") or r.get("end")
            if not start:
                continue
                
            # Parse and format date from start time
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

            # Store ALL sessions for this date
            r["color"] = get_color(r)
            data[project][suite][date].append(r)
            total_reports_count += 1
            
            # Sort sessions by time (newest first)
            data[project][suite][date].sort(key=lambda x: x.get("end", ""), reverse=True)

        # Convert to the format expected by frontend
        data_dict = {}
        for project in data:
            data_dict[project] = {}
            for suite in data[project]:
                data_dict[project][suite] = {}
                for date in data[project][suite]:
                    sessions = data[project][suite][date]
                    data_dict[project][suite][date] = {
                        "sessions": sessions,
                        "latest": sessions[0]  # Most recent session
                    }

        # Prepare final dashboard data structure
        dashboard_data = {
            "data": data_dict,
            "dates": sorted(all_dates_set, reverse=True)[:365],
            "last_updated": (datetime.now() + timedelta(hours=1)).strftime("%d/%m/%Y, %H:%M:%S (GMT+1)")
        }

        # Ensure output directory exists
        os.makedirs(os.path.dirname(DASHBOARD_DATA_FILE), exist_ok=True)
        
        # Write dashboard data to file
        with open(DASHBOARD_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, indent=2, default=str)

        # Create monthly archive if applicable
        create_monthly_archive(dashboard_data)
        
        # Save filtered results back to source
        save_results(results)

        # Output annotations - now showing actual report count
        print(f"📊 Reports processed: {total_reports_count}")
        print(f"Dashboard data updated: {DASHBOARD_DATA_FILE}")
        print(f"Projects: {len(data_dict)}")
        print(f"Last updated: {dashboard_data['last_updated']}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_dashboard_data()
