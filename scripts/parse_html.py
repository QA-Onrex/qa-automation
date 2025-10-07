import os
import json
import shutil
import re
import traceback
from datetime import datetime

HTML_FOLDER = "data/html"
PROCESSED_FOLDER = os.path.join(HTML_FOLDER, "processed")
RESULTS_FILE = "data/results.json"
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load existing results.json
results = []
if os.path.exists(RESULTS_FILE):
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("::warning::results.json is empty or invalid, starting fresh.")
        results = []

def parse_fields_from_html(html_path):
    """Extract test data fields from embedded JSON inside the HTML."""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Extract project info
        project_match = re.search(r'"project":\{"name":"(.*?)"\}', text)
        project = project_match.group(1) if project_match else None

        # Extract test suite ID
        suite_match = re.search(r'"testSuiteId":"(.*?)"', text)
        test_suite_id = suite_match.group(1) if suite_match else None

        # Extract profile
        profile_match = re.search(r'"profile":"(.*?)"', text)
        profile = profile_match.group(1) if profile_match else None

        # Extract test case counts
        passed_match = re.search(r'"passed":(\d+)', text)
        failed_match = re.search(r'"failed":(\d+)', text)
        error_match = re.search(r'"error":(\d+)', text)
        incomplete_match = re.search(r'"incomplete":(\d+)', text)
        skipped_match = re.search(r'"skipped":(\d+)', text)

        # Extract timestamps and duration
        start_match = re.search(r'"start":"(.*?)"', text)
        end_match = re.search(r'"end":"(.*?)"', text)
        duration_match = re.search(r'"duration":([\d\.]+)', text)

        return {
            "html_file": os.path.join("data/html/processed", os.path.basename(html_path)),
            "project": project,
            "test_suite_id": test_suite_id,
            "profile": profile,
            "passed": int(passed_match.group(1)) if passed_match else None,
            "failed": int(failed_match.group(1)) if failed_match else None,
            "error": int(error_match.group(1)) if error_match else None,
            "incomplete": int(incomplete_match.group(1)) if incomplete_match else None,
            "skipped": int(skipped_match.group(1)) if skipped_match else None,
            "start": start_match.group(1) if start_match else None,
            "end": end_match.group(1) if end_match else None,
            "duration": float(duration_match.group(1)) if duration_match else None
        }

    except Exception as e:
        print(f"::error::Failed to parse HTML {html_path}: {e}")
        traceback.print_exc()
        return None

def main():
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to process.")
        return

    processed_count = 0
    for html_file in html_files:
        html_path = os.path.join(HTML_FOLDER, html_file)
        data = parse_fields_from_html(html_path)
        if data:
            results.append(data)
            processed_count += 1
            # Move to processed folder
            shutil.move(html_path, os.path.join(PROCESSED_FOLDER, html_file))
            print(f"::notice::Processed {html_file} and moved to processed folder.")
        else:
            print(f"::warning::Skipping {html_file} due to parsing error.")

    # Save results.json
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"::notice::Updated {RESULTS_FILE} with {processed_count} new entries.")

if __name__ == "__main__":
    main()
