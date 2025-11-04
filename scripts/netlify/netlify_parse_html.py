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
    retry_count = 0
    if not test_suite_id or not start_time or profile is None:
        return 0

    try:
        start_dt = datetime.strptime(start_time.replace('Z', '+0000'), "%Y-%m-%dT%H:%M:%S.%f%z")
        time_threshold = start_dt - timedelta(hours=hours)

        for rec in reversed(results):
            rec_start = rec.get("start")
            if not rec_start:
                continue

            fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if ('+' in rec_start or '-' in rec_start) else "%Y-%m-%dT%H:%M:%S.%fZ"
            rec_dt = datetime.strptime(rec_start.replace('Z', '+0000'), fmt)

            if rec_dt < time_threshold:
                break

            if rec.get("test_suite_id") == test_suite_id and rec.get("profile") == profile:
                retry_count += 1

    except Exception:
        pass

    return retry_count


def _find_listener(node, name="BeforeTestSuite"):
    """Recursively find listener with given name inside the parsed data structure."""
    if not isinstance(node, dict):
        return None
    if node.get("name") == name:
        return node
    # search common containers
    for k in ("listeners", "children", "steps"):
        for c in node.get(k, []):
            found = _find_listener(c, name)
            if found:
                return found
    return None


def _extract_env_from_listener(listener):
    """Search steps and logs inside listener for the browser-open URL message."""
    if not isinstance(listener, dict):
        return None
    url_re = re.compile(r"Browser is opened with url:\s*['\"]?(https?://[^\s'\"\\]+)['\"]?", re.IGNORECASE)
    # Steps may be in 'children' or 'steps'
    for step in (listener.get("children", []) or []) + (listener.get("steps", []) or []):
        # direct message on step
        msg = step.get("message", "") if isinstance(step, dict) else ""
        if msg:
            m = url_re.search(msg)
            if m:
                return m.group(1)
        # logs array inside step
        for log in step.get("logs", []) if isinstance(step, dict) else []:
            lm = (log.get("message") or "")
            if lm:
                m = url_re.search(lm)
                if m:
                    return m.group(1)
    return None


def extract_environment_from_content(content):
    """
    Primary: try to find the URL inside the BeforeTestSuite listener (preferred).
    Fallback: search the entire content for the 'Browser is opened with url' pattern.
    """
    try:
        # Locate the loadExecutionData payload (accept any id like 'main' or '0' etc.)
        match = re.search(r"loadExecutionData\(['\"][^'\"]+['\"],\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if match:
            # isolate JSON block robustly
            simple = re.search(r"(\{.*\})", match.group(0), re.DOTALL)
            payload = simple.group(1) if simple else match.group(1)
            try:
                data_json = json.loads(payload)
            except Exception:
                data_json = None

            if data_json:
                entity = data_json.get("entity", {})
                listener = _find_listener(entity, "BeforeTestSuite")
                env = _extract_env_from_listener(listener) if listener else None
                if env:
                    return env

        # Fallback: scan whole content for the pattern (handles weird cases)
        fallback_re = re.compile(r"Browser is opened with url:\s*(?:\\u0027|['\"])?(https?://[^\s'\"\\]+)(?:\\u0027|['\"])?", re.IGNORECASE)
        m = fallback_re.search(content)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


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

        # Extract environment from listener or fallback scan
        environment = extract_environment_from_content(content)

        # Extract JSON data from HTML content (used for all other metadata)
        match = re.search(r"loadExecutionData\(['\"][^'\"]+['\"],\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"No embedded JSON found in {html_filename}")
            return None

        # isolate the JSON payload
        simple_match = re.search(r"(\{.*\})", match.group(0), re.DOTALL)
        if not simple_match:
            print(f"Failed to isolate JSON from loadExecutionData in {html_filename}")
            return None

        data_json = json.loads(simple_match.group(1))
        entity = data_json.get("entity", {})

        # Extract basic test information
        project_name = data_json.get("project", {}).get("name")
        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")

        # Extract test statistics
        stats = entity.get("statistics", {}) or {}
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
                fmt = "%Y-%m-%dT%H:%M:%S.%f%z" if ('+' in start or '-' in start) else "%Y-%m-%dT%H:%M:%S.%fZ"
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

        # Build result record with environment as first key
        result = {
            "environment": environment,
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

        # Try to remove the local file (we do this after building the result)
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
        urls = load_urls()
        if not urls:
            print("::notice::⏭️ Netlify URLs found: 0")
            return

        files_to_process = []
        for html_filename, netlify_url in urls.items():
            local_path = os.path.join(HTML_FOLDER, html_filename)
            if os.path.exists(local_path):
                files_to_process.append((html_filename, netlify_url))

        if not files_to_process:
            print("::notice::⏭️ HTML files found: 0")
            cleanup_urls_file()
            return

        print(f"::notice::📄 HTML files found: {len(files_to_process)}")

        processed_count = 0

        for html_filename, netlify_url in files_to_process:
            print(f"Parsing HTML file: {html_filename}")
            data = parse_html_from_netlify(html_filename, netlify_url)

            if data:
                # Avoid duplicates: replace existing entry with same html_filename or html_file
                replaced = False
                for i, rec in enumerate(results):
                    if rec.get("html_filename") == data.get("html_filename") or rec.get("html_file") == data.get("html_file"):
                        results[i] = data
                        replaced = True
                        break
                if not replaced:
                    results.append(data)

                processed_count += 1
                print(f"Successfully parsed: {html_filename}")
            else:
                print(f"Failed to parse: {html_filename}")

        # Save updated results
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"::notice::✅ HTML files parsed: {processed_count}")

        cleanup_urls_file()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
