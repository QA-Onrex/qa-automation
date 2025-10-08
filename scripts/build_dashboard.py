import json
import os
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "site/index.html"

def load_results():
    """Load all results from JSON."""
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found.")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_color(record):
    """Determine color based on result logic."""
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    failed = record.get("failed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

    # Sum validation
    total_calc = passed + failed + errored + incomplete + skipped
    if total_calc != total:
        return "red"

    if passed == total:
        return "yellow" if retry > 0 else "green"

    return "red"

def build_dashboard():
    results = load_results()
    if not results:
        print("No results found.")
        return

    # Group data by Project → Test Suite ID → Date
    data = defaultdict(lambda: defaultdict(dict))

    for r in results:
        project = r.get("project", "Unknown")
        suite = r.get("test_suite_id", "Unknown")
        start = r.get("start") or r.get("end")
        if not start:
            continue
        date = datetime.fromisoformat(start.replace("Z", "+00:00")).strftime("%Y.%m.%d")

        # Keep only the latest record for the date
        if date not in data[project][suite] or r.get("end", "") > data[project][suite][date].get("end", ""):
            r["color"] = get_color(r)
            data[project][suite][date] = r

    # Collect all unique dates (reverse order: latest first)
    all_dates = sorted(
        {d for proj in data.values() for suite in proj.values() for d in suite.keys()},
        reverse=True
    )

    # Limit to the last 365 days
    all_dates = all_dates[:365]

    # Build HTML
    html = [
        "<html><head><meta charset='utf-8'><title>QA Automation Report</title>",
        "<style>",
        "body { background-color: #1e1e1e; color: #ddd; font-family: Arial, sans-serif; }",
        "h2 { color: #fff; border-bottom: 2px solid #444; padding-bottom: 4px; }",
        "table { border-collapse: collapse; width: 100%; margin-bottom: 40px; }",
        "th, td { border: 1px solid #444; text-align: center; padding: 6px; }",
        "th { background-color: #2b2b2b; font-weight: bold; }",
        "td.green { background-color: #2e7d32; color: #fff; }",
        "td.yellow { background-color: #f9a825; color: #000; }",
        "td.red { background-color: #c62828; color: #fff; }",
        "td.empty { background-color: #2b2b2b; color: #666; }",
        ".project { font-weight: bold; font-size: 1.2em; color: #fff; padding-top: 10px; }",
        ".suite-name { text-align: left; padding-left: 8px; }",
        "</style></head><body>",
        "<h1>QA Automation Report</h1>"
    ]

    for project in sorted(data.keys()):
        html.append(f"<h2>{project}</h2>")
        html.append("<table>")
        html.append("<tr><th>Test Suite</th>" + "".join(f"<th>{d[5:]}</th>" for d in all_dates) + "</tr>")

        for suite in sorted(data[project].keys()):
            html.append(f"<tr><td class='suite-name'>{suite}</td>")
            for date in all_dates:
                if date in data[project][suite]:
                    record = data[project][suite][date]
                    color = record["color"]
                    passed = record.get("passed", 0)
                    total = record.get("test_cases", 0)
                    failed = total - passed if total else 0
                    html.append(f"<td class='{color}'>{passed}/{failed}</td>")
                else:
                    html.append("<td class='empty'>–</td>")
            html.append("</tr>")

        html.append("</table>")

    html.append("</body></html>")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"✅ Dashboard built successfully: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dashboard()

