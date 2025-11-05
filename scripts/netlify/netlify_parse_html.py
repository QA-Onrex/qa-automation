# scripts/netlify/netlify_parse_html.py
import os
import json
import re
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from netlify_encryptor import decrypt_file_to_bytes

HTML_FOLDER = "data/netlify_html"
URLS_FILE = "data/netlify_urls.json"
RESULTS_FILE = "data/netlify_results.json"
PROCESSED_FOLDER = "docs/netlify_reports"

os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Load existing results for potential later use
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


def _find_listener(node, name="BeforeTestSuite"):
    """Recursively find a listener by name."""
    if not isinstance(node, dict):
        return None
    if node.get("name") == name:
        return node
    for key in ("listeners", "children", "steps"):
        for child in node.get(key, []):
            found = _find_listener(child, name)
            if found:
                return found
    return None


def _extract_env_from_listener(listener):
    """Search steps/logs in listener for the open-browser URL."""
    if not isinstance(listener, dict):
        return None
    pattern = re.compile(r"Browser is opened with url:\s*['\"]?(https?://[^\s'\"\\]+)['\"]?", re.IGNORECASE)
    for step in (listener.get("children", []) or []) + (listener.get("steps", []) or []):
        for message in [step.get("message", "")] + [log.get("message", "") for log in step.get("logs", []) if isinstance(log, dict)]:
            if not message:
                continue
            m = pattern.search(message)
            if m:
                return m.group(1)
    return None


def extract_environment_from_content(content):
    """Primary: extract env URL from BeforeTestSuite; fallback to global regex."""
    try:
        match = re.search(r"loadExecutionData\(['\"][^'\"]+['\"],\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if match:
            payload = match.group(1)
            try:
                data_json = json.loads(payload)
                entity = data_json.get("entity", {})
                listener = _find_listener(entity, "BeforeTestSuite")
                env = _extract_env_from_listener(listener) if listener else None
                if env:
                    return env
            except Exception:
                pass

        # fallback: scan full HTML
        m = re.search(r"Browser is opened with url:\s*(?:\\u0027|['\"])?(https?://[^\s'\"\\]+)", content, re.IGNORECASE)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def parse_html_from_netlify(html_filename, netlify_url):
    """Parse encrypted HTML file and extract raw data."""
    local_path = os.path.join(HTML_FOLDER, html_filename)
    if not os.path.exists(local_path):
        print(f"Local encrypted file not found: {local_path}")
        return None

    try:
        # Decrypt HTML
        html_bytes = decrypt_file_to_bytes(local_path)
        content = html_bytes.decode("utf-8")
        print(f"Decrypting HTML file: {html_filename}")

        # Environment
        environment = extract_environment_from_content(content)

        # Extract JSON payload
        match = re.search(r"loadExecutionData\(['\"][^'\"]+['\"],\s*(\{.*?\})\s*\)", content, re.DOTALL)
        if not match:
            print(f"No embedded JSON found in {html_filename}")
            return None

        data_json = json.loads(match.group(1))
        entity = data_json.get("entity", {})

        # Raw metadata
        project_name = data_json.get("project", {}).get("name")
        test_suite_id = entity.get("entityId")
        profile = entity.get("context", {}).get("profile")
        stats = entity.get("statistics", {}) or {}

        # Test counters
        test_cases = stats.get("total")
        passed = stats.get("passed")
        failed = stats.get("failed")
        error = stats.get("errored")
        incomplete = stats.get("incomplete")
        skipped = stats.get("skipped")

        start = entity.get("startTime")
        end = entity.get("endTime")

        # Raw result only — no derived fields
        result = {
            "netlify_url": netlify_url,
            "html_filename": html_filename,
            "environment": environment,
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
            "end": end
        }

        try:
            os.remove(local_path)
            print(f"Deleted processed file: {html_filename}")
        except Exception as e:
            print(f"Failed to delete local file {local_path}: {e}")

        return result

    except Exception as e:
        print(f"Failed to parse {html_filename}: {e}")
        return None


def cleanup_urls_file():
    """Remove URLs file after processing completion."""
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

        files_to_process = [
            (f, url) for f, url in urls.items()
            if os.path.exists(os.path.join(HTML_FOLDER, f))
        ]

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
                # Replace existing by filename
                results[:] = [
                    r for r in results if r.get("html_filename") != html_filename
                ]
                results.append(data)
                processed_count += 1
                print(f"Successfully parsed: {html_filename}")
            else:
                print(f"Failed to parse: {html_filename}")

        # Save results
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"::notice::✅ HTML files parsed: {processed_count}")
        cleanup_urls_file()

        # Call the separate script to update the version file
        version_script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "netlify_version_manager.py"
        )
        # Execute the version manager script
        os.system(f"python {version_script_path}")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
