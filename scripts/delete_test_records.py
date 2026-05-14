# delete_test_records.py
import json
import os
import sys

# Configuration
RESULTS_FILE = "D:/PyCharm_Project/qa-automation/data/results.json"

# Hardcoded test name to delete
test_name = "Test Suites/GU Interface (all)"


def load_results():
    """Load test results from JSON file"""
    if not os.path.exists(RESULTS_FILE):
        print(f"❌ Results file not found: {RESULTS_FILE}")
        return []
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: {RESULTS_FILE} is not valid JSON")
        return []


def save_results(results):
    """Save results back to JSON file"""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated {RESULTS_FILE}")


def delete_records_by_test_name(results, test_name):
    """Delete all records matching the test name (by test_suite_id)"""
    original_count = len(results)
    deleted_records = []
    filtered_results = []

    for record in results:
        # Match by test_suite_id
        if record.get("test_suite_id") == test_name:
            deleted_records.append(record)
        else:
            filtered_results.append(record)

    deleted_count = len(deleted_records)

    if deleted_count > 0:
        print(f"🗑️  Deleted {deleted_count} record(s) for test: '{test_name}'")
        print(f"   Remaining records: {len(filtered_results)}")

        # Show details of deleted records
        for record in deleted_records:
            html_file = record.get("html_filename", "unknown")
            start_time = record.get("start", "unknown")
            print(f"   - {html_file} ({start_time})")
    else:
        print(f"⚠️  No records found for test: '{test_name}'")

    return filtered_results, deleted_count


def main():
    print(f"🔍 Loading results from {RESULTS_FILE}...")
    results = load_results()

    if not results:
        print("❌ No results to process")
        return

    print(f"📊 Total records found: {len(results)}")
    print(f"🎯 Looking for test: '{test_name}'")
    print("-" * 60)

    filtered_results, deleted_count = delete_records_by_test_name(results, test_name)

    if deleted_count > 0:
        print("-" * 60)
        save_results(filtered_results)
        print("\n✅ Records successfully deleted!")
        print("💡 Next steps:")
        print("   1. Run: python scripts/generate_dashboard.py")
        print("   2. Run: python scripts/version_manager.py")
        print("   3. Dashboard will refresh within 30 seconds")
    else:
        print("❌ No changes made")


if __name__ == "__main__":
    main()