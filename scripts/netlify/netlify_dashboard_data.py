# scripts/netlify/netlify_dashboard_data.py
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
    
    The keys (dates) and values (run data) from the original JSON are converted 
    into two separate lists for easy client-side rendering.
    """
    dates = []
    run_data = []

    # Iterate through the chronological data from newest to oldest (as Python dicts are ordered)
    for date, runs in results_data.items():
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
