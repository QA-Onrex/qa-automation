# scripts/netlify/prepare_dashboard_data.py
import json
import os
import sys

# Define file paths based on standard project structure
RESULTS_FILE = "data/netlify_results.json"
OUTPUT_FILE = "docs/dashboard_data.json"
OUTPUT_DIR = os.path.dirname(OUTPUT_FILE)

# --- Utility Functions ---
def get_color_class(status):
    """Maps status text to a CSS class for coloring."""
    if status == "Failed":
        return "status-failed"
    elif status == "Passed":
        return "status-passed"
    elif status == "No Run" or status == "N/A":
        return "status-neutral"
    elif status == "Skipped":
        return "status-skipped"
    return "status-neutral"

def prepare_data_for_frontend(results_data):
    """
    Transforms a list of individual report records into the date-matrix format 
    required for the frontend dashboard.
    """
    # 1. Normalize input: Ensure 'records' is a list of dictionaries
    records = []
    if isinstance(results_data, list):
        # Case 1: The correct historical format (list of all reports)
        records = results_data
    elif isinstance(results_data, dict):
        # Case 2: The single report dictionary (treat as a list of one report)
        records = [results_data]
    else:
        print(f"::error::Results data is an unknown format ({type(results_data)}). Returning empty dashboard.")
        return {"dates": [], "runs": [], "run_identifiers": []}
        
    # --- Aggregation Step ---
    # Target structure: { "YYYY-MM-DD": { "Run_ID": {report data} } }
    aggregated_data = {}
    
    for record in records:
        # Check if the record is a string and try to parse it (resilience check)
        if isinstance(record, str):
            try:
                record = json.loads(record)
            except json.JSONDecodeError:
                print(f"::warning::Skipping unparsable JSON string record.")
                continue

        if not isinstance(record, dict):
             print(f"::warning::Skipping non-dictionary record.")
             continue

        # Extract date and create a unique identifier for the run slot
        try:
            start_datetime = record.get("start")
            if not start_datetime: continue

            # Get YYYY-MM-DD
            date = start_datetime.split('T')[0] 
            
            # Create a comprehensive unique identifier for the test suite slot
            # The client needs this to build columns consistently.
            run_id = f"{record.get('project', 'Unknown')} - {record.get('test_suite_id', 'UnknownSuite')} - {record.get('profile', 'UnknownProfile')}"
            
        except (KeyError, IndexError, AttributeError):
            print(f"::warning::Skipping record due to missing or malformed 'start' or identifier fields.")
            continue

        if date not in aggregated_data:
            aggregated_data[date] = {}
        
        # Determine Status and Class
        status = "Passed" if record.get("failed", 0) == 0 else "Failed"
        
        # Store the simplified record
        aggregated_data[date][run_id] = {
            "status": status,
            "status_class": get_color_class(status),
            "timestamp": start_datetime,
            "html_file": record.get("html_filename", "N/A"),
            # Ensure the link is relative to the Netlify reports directory
            "html_link": f"/reports/{record.get('html_filename')}" if record.get('html_filename') else "#",
            "browser": record.get("profile", "N/A"), # Using 'profile' as browser/env for display
        }

    # 2. Final preparation for the client: extract dates and run lists
    dates = sorted(aggregated_data.keys(), reverse=True) # Sort dates newest first

    # Create a list of all unique run identifiers to establish consistent column order
    all_run_ids = sorted(list(set(run_id for date_data in aggregated_data.values() for run_id in date_data.keys())))
    
    # Structure the run data row by row (one element per date)
    run_data_list = []
    
    for date in dates:
        date_runs = []
        for run_id in all_run_ids:
            # Find the run record for this specific date and run_id, or use a placeholder
            record = aggregated_data[date].get(run_id, {
                "status": "No Run",
                "status_class": "status-neutral",
                "timestamp": "N/A",
                "html_file": "N/A",
                "html_link": "#",
                "browser": "N/A"
            })
            date_runs.append(record)
        run_data_list.append(date_runs)


    return {
        "dates": dates,
        "runs": run_data_list,
        "run_identifiers": all_run_ids # New key to help client draw headers
    }

# --- Main Execution ---
def main():
    if not os.path.exists(RESULTS_FILE):
        print(f"::error::Input file not found: {RESULTS_FILE}")
        sys.exit(1)

    try:
        # Load the data. This will load the list or dictionary at the root level.
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
