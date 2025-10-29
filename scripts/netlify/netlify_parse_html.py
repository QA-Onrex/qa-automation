# scripts/netlify/netlify_parse_html.py
import os
import json
import re
import requests
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_bytes_to_bytes

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"
RESULTS_FILE = "data/netlify_results.json"
PROCESSED_FOLDER = "docs/netlify_reports"
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load existing results
results = []
if os.path.exists(RESULTS_FILE):
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("::warning::netlify_results.json is empty or invalid, starting fresh.")
        results = []

def load_urls():
    """Load Netlify URLs mapping."""
    if os.path.exists(URLS_FILE):
        try:
            with open(URLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def fetch_encrypted_html_from_netlify(url):
    """Fetch encrypted HTML from Netlify."""
    try:
        print(f"::notice::Fetching from Netlify: {url}")
        response = requests.get(url)
        print(f"::notice::Netlify response status: {response.status_code}")
        
        if response.status_code == 200:
            content_length = len(response.content)
            print(f"::notice::Successfully fetched {content_length} bytes from Netlify")
            return response.content
        else:
            print(f"::error::Failed to fetch from Netlify: {response.status_code} - {response.text[:200]}")
            return None
    except Exception as e:
        print(f"::error::Error fetching from Netlify: {e}")
        traceback.print_exc()
        return None

def compute_retry_count(test_suite_id, start_time, results, hours=10):
    """Compute retry count using chronological results, stop when older than 10 hours."""
    retry_count = 0
    if not test_suite_id or not start_time:
        return 0
    try:
        start_dt = datetime.strptime(start_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
        time_threshold = start_dt - timedelta(hours=hours)

        # Iterate results in reverse chronological order
        for rec in reversed(results):
            rec_start = rec.get("start")
            if not rec_start:
                continue
            rec_dt = datetime.strptime(rec_start.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")

            # Stop as soon as the record is older than 10 hours
            if rec_dt < time_threshold:
                break

            if rec.get("test_suite_id") == test_suite_id:
                retry_count += 1

    except Exception:
        pass

    return retry_count

def parse_html_from_netlify(html_filename, netlify_url):
    """Fetch, decrypt and parse embedded JSON from Netlify HTML."""
    try:
        # Fetch encrypted HTML from Netlify
        encrypted_bytes = fetch_encrypted_html_from_netlify(netlify_url)
        if not encrypted_bytes:
            print(f"::error::Failed to fetch {html_filename} from Netlify")
            return None

        # Decrypt HTML in memory
        html_bytes = decrypt_bytes_to_bytes(encrypted_bytes)
        content = html_bytes.decode("utf-8")

        # Extract JSON inside loadExecutionData('main', {...})
        match = re.search(r"loadExecutionData\('main',\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"::warning::No embedded JSON found in {html_filename}")
            return None

        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        # Project is outside entity
        project_name = data_json.get("project", {}).get("name")

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

        # Compute duration in minutes
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in start or '-' in start else "%Y-%m-%dT%H:%M:%S.%fZ"
                start_dt = datetime.strptime(start.replace('Z', '+0000'), fmt)
                end_dt = datetime.strptime(end.replace('Z', '+0000'), fmt)
                duration = (end_dt - start_dt).total_seconds() / 60  # minutes
            except Exception:
                duration = None

        # Compute retry count dynamically
        retry_count = compute_retry_count(test_suite_id, start, results)

        # Sum check
        sum_check = True
        if test_cases is not None:
            total_sum = sum(filter(None, [passed, failed, error, incomplete, skipped]))
            sum_check = (total_sum == test_cases)

        # Color logic
        color = "Red"  # default
        if test_cases is not None and passed == test_cases and sum_check:
            color = "Green"
            if retry_count and retry_count != 0:
                color = "Yellow"

        return {
            "html_file": netlify_url,  # Store Netlify URL instead of local path
            "html_filename": html_filename,
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
            "retry_count": retry_count,
            "sum_check": sum_check,
            "color": color
        }

    except Exception as e:
        print(f"::error::Failed to parse {html_filename}: {e}")
        return None

def main():
    urls = load_urls()
    if not urls:
        print("::notice::No Netlify URLs found to process.")
        return

    processed_count = 0
    for html_filename, netlify_url in urls.items():
        data = parse_html_from_netlify(html_filename, netlify_url)
        if data:
            results.append(data)
            processed_count += 1
            print(f"::notice::Processed {html_filename} from Netlify.")
        else:
            print(f"::warning::Skipping {html_filename} due to parsing error.")

    # Save results.json unencrypted
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"::notice::Updated {RESULTS_FILE} with {processed_count} new entries.")

if __name__ == "__main__":
    main()
