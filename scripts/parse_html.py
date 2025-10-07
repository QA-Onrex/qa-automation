import os
import json
import shutil
import re
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

def parse_html_file(html_path):
    """Parse embedded JSON from HTML and extract all test data fields."""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract JSON inside loadExecutionData('main', {...})
        match = re.search(r"loadExecutionData\('main',\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"::warning::No embedded JSON found in {html_path}")
            return None

        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        # Extract all fields in one place
        project_name = entity["project"]["name"]  # always present
        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")

        stats = entity.get("statistics", {})
        test_cases = stats.get("total")
        passed = stats.get("passed")
        failed = stats.get("failed")
        error = stats.get("errored")
        incomplete = stats.get("incomplete")
        skipped = stats.get("skipped")

        start = entity.get("startTime")
        end = entity.get("endTime")
        retry_count = entity.get("retryCount")

        # Compute duration in seconds if start and end are available
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in start or '-' in start else "%Y-%m-%dT%H:%M:%S.%fZ"
                start_dt = datetime.strptime(start.replace('Z', '+0000'), fmt)
                end_dt = datetime.strptime(end.replace('Z', '+0000'), fmt)
                duration = (end_dt - start_dt).total_seconds()
            except Exception:
                duration = None

        return {
            "html_file": os.path.join("data/html/processed", os.path.basename(html_path)),
            "project": project_name,
            "test_suite_id": test_suite_id,
            "profile": profile,
            "test_cases": test_cases,
            "passed": passed,
            "failed": failed,
            "error": error,
            "incomplete": incomplete,
            "skipped": skipped,
            "start": start,
            "end": end,
            "duration": duration,
            "retry_count": retry_count
        }

    except Exception as e:
        print(f"::error::Failed to parse {html_path}: {e}")
        return None

def main():
    html_files = [f for f in os.listdir(HTML_FOLDER) if f.lower().endswith(".html")]
    if not html_files:
        print("::notice::No HTML files to process.")
        return

    processed_count = 0
    for html_file in html_files:
        html_path = os.path.join(HTML_FOLDER, html_file)
        data = parse_html_file(html_path)
        if data:
            results.append(data)
            processed_count += 1
            shutil.move(html_path, os.path.join(PROCESSED_FOLDER, html_file))
            print(f"::notice::Processed {html_file} and moved to processed folder.")
        else:
            print(f"::warning::Skipping {html_file} due to parsing error.")

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"::notice::Updated {RESULTS_FILE} with {processed_count} new entries.")

if __name__ == "__main__":
    main()
