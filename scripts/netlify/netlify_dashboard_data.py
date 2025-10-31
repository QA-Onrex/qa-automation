# scripts/netlify/prepare_dashboard_data.py
import json
import os
import sys

# Define file paths based on standard project structure
RESULTS_FILE = "data/netlify_results.json"
OUTPUT_FILE = "docs/dashboard_data.json"
OUTPUT_DIR = os.path.dirname(OUTPUT_FILE)

# --- Utility Functions (Simplified for demonstration) ---
def get_color_class(status):
    """Maps status text to a CSS class for coloring."""
    if "Failed" in status:
        return "status-failed"
    elif "Passed" in status:
        return "status-passed"
    elif "Skipped" in status:
        return "status-skipped"
    return "status-neutral"

def prepare_data_for_frontend(results_data):
    """
    Transforms the structured results data into a flat, client-ready format.
    
    Handles the case where the JSON data is erroneously wrapped in a list
    and where nested dictionaries are stored as strings.
    """
    # FIX 1: Handle data incorrectly wrapped in a list (outer layer)
    if isinstance(results_data, list):
        if len(results_data) == 1 and isinstance(results_data[0], dict):
            print("::warning::Detected data incorrectly wrapped in a list; unwrapping...")
            results_data = results_data[0]
        else:
            print("::error::Results data is a list with unexpected content. Cannot proceed.")
            return {"dates": [], "runs": []}

    dates = []
    run_data = []

    for date, runs in results_data.items():
        # FIX 2: Handle data incorrectly stored as a string (inner layer)
        if isinstance(runs, str):
            try:
                # Attempt to parse the string back into a dictionary
                runs = json.loads(runs)
                print(f"::warning::Parsed JSON string for date {date}.")
            except json.JSONDecodeError:
                print(f"::error::Could not decode JSON string for date {date}. Skipping this entry.")
                continue
        
        # Ensure 'runs' is now a dictionary before proceeding
        if not isinstance(runs, dict):
             print(f"::error::Runs data for date {date} is neither a dict nor a parsable string. Skipping.")
             continue

        dates.append(date)
        
        # Prepare the list of runs for this date
        date_runs = []
        for run_id, record in runs.items():
            # Create a simplified record for the client
            date_runs.append({
                "id": run_id,
                "browser": record.get("browser", "N/A"),
                "env": record.get("env", "N/A"),
                "status": record.get("status", "N/A"),
                "status_class": get_color_class(record.get("status", "")),
                "timestamp": record.get("timestamp", "N/A"),
                "html_file": record.get("html_file", "N/A"),
                "html_link": f"/reports/{record.get('html_file')}" if record.get('html_file') else "#" 
            })
        run_data.append(date_runs)

    return {
        "dates": dates,
        "runs": run_data
    }

# --- Main Execution ---
def main():
    if not os.path.exists(RESULTS_FILE):
        print(f"::error::Input file not found: {RESULTS_FILE}")
        sys.exit(1)

    try:
        with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
    except json.JSONDecodeError:
        print(f"::error::Failed to decode JSON from {RESULTS_FILE}")
        sys.exit(1)

    # 1. Prepare the data structure
    dashboard_data = prepare_data_for_frontend(results_data)

    # 2. Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 3. Write the simplified JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Successfully created dynamic dashboard data at {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
