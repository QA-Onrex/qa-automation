# scripts/netlify/netlify_parse_html.py
import os
import json
import re
import requests # Still imported but unused in primary function
from datetime import datetime, timedelta
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# NOTE: decrypt_file_to_bytes is now used to read the local encrypted HTML file
from netlify_encryptor import decrypt_file_to_bytes

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

def compute_retry_count(test_suite_id, start_time, results, hours=10):
    """Compute retry count using chronological results, stop when older than 10 hours."""
    retry_count = 0
    if not test_suite_id or not start_time:
        return 0
    try:
        # Fix date parsing if needed (the previous script had a bug here: ret.get("start"))
        start_dt = datetime.strptime(start_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
        time_threshold = start_dt - timedelta(hours=hours)

        # Iterate results in reverse chronological order
        for rec in reversed(results):
            # NOTE: Fixed the variable name from 'ret' to 'rec'
            rec_start = rec.get("start")
            if not rec_start:
                continue
            # Handle potential non-uniform datetime formats (from the original script's logic)
            fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in rec_start or '-' in rec_start else "%Y-%m-%dT%H:%M:%S.%fZ"
            rec_dt = datetime.strptime(rec_start.replace('Z', '+0000'), fmt)

            # Stop as soon as the record is older than 10 hours
            if rec_dt < time_threshold:
                break

            if rec.get("test_suite_id") == test_suite_id:
                # Only count *previous* runs, the current record being processed shouldn't count as a retry for itself
                # The count will be applied to the new record *after* this loop finishes.
                retry_count += 1 

    except Exception:
        pass

    return retry_count

def parse_html_from_netlify(html_filename, netlify_url):
    """Decrypt, parse embedded JSON from local HTML file, and delete the file."""
    local_path = os.path.join(HTML_FOLDER, html_filename)
    
    if not os.path.exists(local_path):
        print(f"::warning::Local encrypted file not found: {local_path}")
        return None

    try:
        # Decrypt HTML from local file into memory
        # Uses the decrypt_file_to_bytes function from netlify_encryptor
        print(f"::notice::Decrypting local file: {local_path}")
        html_bytes = decrypt_file_to_bytes(local_path)
        content = html_bytes.decode("utf-8")

        # Extract JSON inside loadExecutionData('main', {...})
        match = re.search(r"loadExecutionData\('main',\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"::warning::No embedded JSON found in {html_filename}")
            return None

        # --- Parsing Logic (Unchanged) ---
        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        project_name = data_json.get("project", {}).get("name")
        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")
        
        # ... (statistics extraction is unchanged)
        stats = entity.get("statistics", {})
        test_cases = stats.get("total")
        passed = stats.get("passed")
        failed = stats.get("failed")
        error = stats.get("errored")
        incomplete = stats.get("incomplete")
        skipped = stats.get("skipped")

        start = entity.get("startTime")
        end = entity.get("endTime")

        # Compute duration in minutes (unchanged)
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in start or '-' in start else "%Y-%m-%dT%H:%M:%S.%fZ"
                # Use .replace('Z', '+0000') only if the string contains 'Z' and not a timezone offset
                start_str = start.replace('Z', '+0000') if 'Z' in start and '+' not in start and '-' not in start else start
                end_str = end.replace('Z', '+0000') if 'Z' in end and '+' not in end and '-' not in end else end
                
                start_dt = datetime.strptime(start_str, fmt)
                end_dt = datetime.strptime(end_str, fmt)
                duration = (end_dt - start_dt).total_seconds() / 60  # minutes
            except Exception:
                duration = None
                
        # Compute retry count dynamically
        # NOTE: The current record is *not* in 'results' yet, so the count is for previous runs.
        retry_count = compute_retry_count(test_suite_id, start, results)

        # Sum check (unchanged)
        sum_check = True
        if test_cases is not None:
            total_sum = sum(filter(None, [passed, failed, error, incomplete, skipped]))
            sum_check = (total_sum == test_cases)

        # Color logic (unchanged)
        color = "Red"  # default
        if test_cases is not None and passed == test_cases and sum_check:
            color = "Green"
            if retry_count and retry_count != 0:
                color = "Yellow"

        result = {
            "html_file": netlify_url, # KEEP the Netlify URL for the dashboard link
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
        
        # --- CRITICAL CHANGE: DELETE LOCAL FILE AFTER SUCCESSFUL PARSING ---
        try:
            os.remove(local_path)
            print(f"::notice::Successfully deleted local file: {local_path}")
        except Exception as delete_e:
            print(f"::error::Failed to delete local file {local_path}: {delete_e}")
            
        return result

    except Exception as e:
        print(f"::error::Failed to parse {html_filename} from local disk: {e}")
        # Ensure file is NOT deleted if parsing fails
        return None

def cleanup_urls_file():
    """Clean up the URLs file after successful processing."""
    try:
        if os.path.exists(URLS_FILE):
            os.remove(URLS_FILE)
            print(f"::notice::Successfully cleaned up {URLS_FILE}")
    except Exception as e:
        print(f"::warning::Failed to clean up {URLS_FILE}: {e}")

def main():
    urls = load_urls()
    if not urls:
        print("::notice::No Netlify URLs found to process (waiting for upload step).")
        return

    # Check if there are any local files to process
    files_to_process = []
    for html_filename, netlify_url in urls.items():
        local_path = os.path.join(HTML_FOLDER, html_filename)
        if os.path.exists(local_path):
            files_to_process.append((html_filename, netlify_url))
    
    if not files_to_process:
        print("::notice::No local HTML files found to process. Cleaning up URLs file.")
        cleanup_urls_file()
        return

    processed_count = 0
    
    # Iterate through the files that actually exist locally
    for html_filename, netlify_url in files_to_process:
        data = parse_html_from_netlify(html_filename, netlify_url)
        
        if data:
            results.append(data)
            processed_count += 1
            print(f"::notice::Processed {html_filename} from local disk.")
        else:
            print(f"::warning::Skipping {html_filename} - failed to parse or file missing locally.")

    # Save results.json unencrypted
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"::notice::Updated {RESULTS_FILE} with {processed_count} new entries.")
    
    # Clean up URLs file after successful processing
    cleanup_urls_file()

if __name__ == "__main__":
    main()
