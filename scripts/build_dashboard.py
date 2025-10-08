import json
import os
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"

def build_dashboard():
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    # Group by project → test_suite_id → date
    data = defaultdict(lambda: defaultdict(dict))
    for entry in results:
        project = entry.get("project", "Unknown Project")
        suite = entry.get("test_suite_id", "Unknown Suite").replace("Test Suites/", "")
        date = entry.get("start", "")[:10] if entry.get("start") else "Unknown"
        data[project][suite][date] = entry

    # Collect all dates, latest first
    all_dates = sorted({d for p in data.values() for s in p.values() for d in s.keys()}, reverse=True)

    # HTML header
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Automation Dashboard</title>
<style>
body {
  background-color: #121212;
  color: #e0e0e0;
  font-family: Arial, sans-serif;
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: max-content;
  min-width: 100%;
}
th, td {
  border: 1px solid #333;
  padding: 6px 12px;
  text-align: center;
  white-space: nowrap;
}
th {
  background-color: #222;
  position: sticky;
  top: 0;
  z-index: 2;
}
.project {
  background-color: #1e1e1e;
  font-weight: bold;
}
.suite-name {
  text-align: left;
  font-weight: normal;
  background-color: #1a1a1a;
  position: sticky;
  left: 0;
  z-index: 1;
  min-width: 300px;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tooltip {
  position: relative;
  display: inline-block;
}
.tooltip .tooltiptext {
  visibility: hidden;
  width: 220px;
  background-color: #333;
  color: #fff;
  text-align: left;
  border-radius: 6px;
  padding: 10px;
  position: absolute;
  z-index: 3;
  bottom: 125%;
  left: 50%;
  margin-left: -110px;
  opacity: 0;
  transition: opacity 0.3s;
  white-space: normal;
}
.tooltip:hover .tooltiptext {
  visibility: visible;
  opacity: 1;
}
.green { background-color: #2e7d32; color: white; }
.yellow { background-color: #fbc02d; color: black; }
.red { background-color: #c62828; color: white; }
</style>
</head>
<body>
<h1>Automation Test Dashboard</h1>
<table>
<tr><th>Test Suite</th>"""

    for d in all_dates:
        html += f"<th>{d[5:]}</th>"  # show MM-DD (omit year)
    html += "</tr>"

    for project, suites in sorted(data.items()):
        html += f"<tr class='project'><td colspan='{len(all_dates) + 1}'>{project}</td></tr>"
        for suite, results_by_date in sorted(suites.items()):
            html += f"<tr><td class='suite-name'>{suite}</td>"
            for d in all_dates:
                entry = results_by_date.get(d)
                if not entry:
                    html += "<td></td>"
                    continue

                # Compute summary
                total = entry.get("test_cases", 0)
                passed = entry.get("passed", 0)
                failed = total - passed
                color = entry.get("color", "red")

                # Tooltip content
                tooltip = (
                    f"Test Cases: {total}\n"
                    f"Passed: {passed}\n"
                    f"Failed: {entry.get('failed', 0)}\n"
                    f"Error: {entry.get('error', 0)}\n"
                    f"Incomplete: {entry.get('incomplete', 0)}\n"
                    f"Skipped: {entry.get('skipped', 0)}\n"
                    f"Retry: {entry.get('retry_count', 0)}\n"
                    f"Start: {entry.get('start', '')}\n"
                    f"End: {entry.get('end', '')}\n"
                    f"Duration: {entry.get('duration', '')} min"
                )
                tooltip_html = tooltip.replace("\n", "<br>")

                # HTML report link (stored in docs/reports/)
                html_file = os.path.basename(entry["html_file"])
                link = f"reports/{html_file}"

                html += (
                    f"<td class='{color} tooltip'>"
                    f"<a href='{link}' target='_blank'>{passed}/{failed}</a>"
                    f"<span class='tooltiptext'>{tooltip_html}</span></td>"
                )

            html += "</tr>"

    html += "</table></body></html>"

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard built successfully: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dashboard()
