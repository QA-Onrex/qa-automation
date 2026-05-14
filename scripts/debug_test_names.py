# debug_test_names.py
import json
import os

RESULTS_FILE = "D:/PyCharm_Project/qa-automation/data/results.json"


def debug_test_names():
    """Print all unique test_suite_id values to find the exact name"""
    if not os.path.exists(RESULTS_FILE):
        print(f"❌ Results file not found: {RESULTS_FILE}")
        return

    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: {RESULTS_FILE} is not valid JSON")
        return

    # Get unique test_suite_id values
    test_names = {}
    for record in results:
        name = record.get("test_suite_id")
        if name:
            if name not in test_names:
                test_names[name] = 0
            test_names[name] += 1

    print(f"📊 Found {len(test_names)} unique tests:\n")

    # Sort by count (most frequent first)
    sorted_tests = sorted(test_names.items(), key=lambda x: x[1], reverse=True)

    for name, count in sorted_tests:
        print(f"  [{count:4d}] {name}")

    # Search for "Verify Receiver"
    print("\n🔍 Tests containing 'Accept order':")
    for name, count in sorted_tests:
        if "Accept order" in name:
            print(f"  [{count:4d}] {name}")


if __name__ == "__main__":
    debug_test_names()