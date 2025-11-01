# scripts/netlify/netlify_parse_html.py
import os
import json
import re
from datetime import datetime, timedelta
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_file_to_bytes

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"
RESULTS_FILE = "data/netlify_results.json"
PROCESSED_FOLDER = "docs/netlify_reports"

os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load existing results for retry count calculation
results = []
if os.path.exists(RESULTS_FILE):
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
    except json.JSONDecodeError:
        print("netlify_results.json is empty or invalid, starting fresh")
        results = []


def load_urls():
    """Load URL mappings from previous upload step"""
    if os.path.exists(URLS_FILE):
        try:
            with open(URLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def compute_retry_count(test_suite_id, profile, start_time, results, hours=10):
    """
    Calculate retry count for a test suite within a specified time window,
    only counting previous runs that used the EXACT SAME PROFILE.
    """
    # Initialize count. We start at 0 because the current run is not a retry of itself.
    retry_count = 0
    if not test_suite_id or not start_time or profile is None:
        return 0
        
    try:
        # 1. Parse current test run start time
        # Replace 'Z' with '+0000' for consistent datetime parsing across formats
        start_dt = datetime.strptime(start_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
        time_threshold = start_dt - timedelta(hours=hours)

        # 2. Check previous runs in reverse chronological order
        for rec in reversed(results):
            rec_start = rec.get("start")
            
            # Skip records without a start time
            if not rec_start:
                continue
                
            # Handle different datetime formats for previous records
            fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in rec_start or '-' in rec_start else "%Y-%m-%dT%H:%M:%S.%fZ"
            rec_dt = datetime.strptime(rec_start.replace('Z', '+0000'), fmt)

            # Stop when reaching records older than time threshold
            if rec_dt < time_threshold:
                break

            # 3. COUNTING CONDITION (The critical modification)
            # Count previous runs ONLY if they match BOTH the Test Suite ID AND the Profile.
            is_same_suite = rec.get("test_suite_id") == test_suite_id
            is_same_profile = rec.get("profile") == profile
            
            if is_same_suite and is_same_profile:
                retry_count += 1

    except Exception:
        # In a real-world scenario, you might want to log the exception here
        pass

    return retry_count

def parse_html_from_netlify(html_filename, netlify_url):
    """Parse encrypted HTML file to extract test results and metadata"""
    local_path = os.path.join(HTML_FOLDER, html_filename)
    
    if not os.path.exists(local_path):
        print(f"Local encrypted file not found: {local_path}")
        return None

    try:
        # Decrypt HTML file content
        html_bytes = decrypt_file_to_bytes(local_path)
        content = html_bytes.decode("utf-8")
        print(f"Decrypting HTML file: {html_filename}")

        # Extract JSON data from HTML content
        match = re.search(r"loadExecutionData\('main',\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"No embedded JSON found in {html_filename}")
            return None

        # Parse test execution data from JSON
        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        # Extract basic test information
        project_name = data_json.get("project", {}).get("name")
        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")
        
        # Extract test statistics
        stats = entity.get("statistics", {})
        test_cases = stats.get("total")
        passed = stats.get("passed")
        failed = stats.get("failed")
        error = stats.get("errored")
        incomplete = stats.get("incomplete")
        skipped = stats.get("skipped")

        # Extract timing information
        start = entity.get("startTime")
        end = entity.get("endTime")

        # Calculate test duration
        duration = None
        if start and end:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if '+' in start or '-' in start else "%Y-%m-%dT%H:%M:%S.%fZ"
                start_str = start.replace('Z', '+0000') if 'Z' in start and '+' not in start and '-' not in start else start
                end_str = end.replace('Z', '+0000') if 'Z' in end and '+' not in end and '-' not in end else end
                
                start_dt = datetime.strptime(start_str, fmt)
                end_dt = datetime.strptime(end_str, fmt)
                duration = (end_dt - start_dt).total_seconds() / 60
            except Exception:
                duration = None
                
        # Calculate retry count from previous runs
        retry_count = compute_retry_count(test_suite_id, profile, start, results)

        # Validate test case counts
        sum_check = True
        if test_cases is not None:
            total_sum = sum(filter(None, [passed, failed, error, incomplete, skipped]))
            sum_check = (total_sum == test_cases)

        # Determine test result color
        color = "Red"
        if test_cases is not None and passed == test_cases and sum_check:
            color = "Green"
            if retry_count and retry_count != 0:
                color = "Yellow"

        # Build result record
        result = {
            "html_file": netlify_url,
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
        
        # Clean up processed HTML file
        try:
            os.remove(local_path)
            print(f"Deleted processed file: {html_filename}")
        except Exception as delete_e:
            print(f"Failed to delete local file {local_path}: {delete_e}")
            
        return result

    except Exception as e:
        print(f"Failed to parse {html_filename}: {e}")
        return None


def cleanup_urls_file():
    """Remove URLs file after processing completion"""
    try:
        if os.path.exists(URLS_FILE):
            os.remove(URLS_FILE)
            print(f"Cleaned up URLs file: {URLS_FILE}")
    except Exception as e:
        print(f"Failed to clean up {URLS_FILE}: {e}")


def main():
    try:
        # Load URLs from upload step
        urls = load_urls()
        if not urls:
            print("::notice::⏭️ Netlify URLs found: 0")
            return

        # Find local files that match URLs
        files_to_process = []
        for html_filename, netlify_url in urls.items():
            local_path = os.path.join(HTML_FOLDER, html_filename)
            if os.path.exists(local_path):
                files_to_process.append((html_filename, netlify_url))
        
        # Exit early if no files to process
        if not files_to_process:
            print("::notice::⏭️ HTML files found: 0")
            cleanup_urls_file()
            return

        # Output annotation for found files
        print(f"::notice::📄 HTML files found: {len(files_to_process)}")

        processed_count = 0
        
        # Process each HTML file
        for html_filename, netlify_url in files_to_process:
            print(f"Parsing HTML file: {html_filename}")
            data = parse_html_from_netlify(html_filename, netlify_url)
            
            if data:
                results.append(data)
                processed_count += 1
                print(f"Successfully parsed: {html_filename}")
            else:
                print(f"Failed to parse: {html_filename}")

        # Save updated results
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Output annotation for processed files
        print(f"::notice::✅ HTML files parsed: {processed_count}")
        
        # Clean up URLs file
        cleanup_urls_file()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
