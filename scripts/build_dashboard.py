import os
import json
from datetime import datetime

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"
HTML_FOLDER = "data/html/processed"

# Load results
with open(RESULTS_FILE, "r", encoding="utf-8") as f:
    results = json.load(f)

# Organize by project and test_suite_id
projects = {}
for r in results:
    project = r["project"]
    suite = r["test_suite_id"] or "N/A"
    if project not in projects:
        projects[project] = {}
    if suite not in projects[project]:
        projects[project][suite] = []
    projects[project][suite].append(r)

# For each suite, keep only latest entry per day
for project in projects:
    for suite in projects[project]:
        # Sort by end time descending
        projects[project][suite].sort(key=lambda x: x.get("end") or "", reverse=True)
        daily = {}
        filtered = []
        for entry in projects[project][suite]:
            if entry.get("end"):
                day = entry["end"][:10]  # YYYY-MM-DD
            else:
                day = "N/A"
            if day not in daily:
                daily[day] = entry
                filtered.append(entry)
        projects[project][suite] = filtered

# Generate list of all dates for columns, descending
all_dates = set()
for project in projects.values():
    for suite_entries in project.values():
        for entry in suite_entries:
            if entry.get("end"):
                all_dates.add(entry["end"][:10])
dates_sorted = sorted(all_dates, reverse=True)

# Start building HTML
html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QA Automation Dashboard</title>
<style>
body {
    margin: 0;
    padding: 0;
    background-color: #121212;
    color: #eee;
    font-family: Arial, sans-serif;
    overflow: hidden; /* remove page scroll */
}
.table-container {
    width: 100%;
    height: 95vh;
    overflow: auto;
    position: relative;
}
table {
    border-collapse: collapse;
    table-layout: fixed;
    width: max-content;
    min-width: 100%;
}
th, td {
    border: 1px solid #333;
    padding: 5px;
    text-align: center;
    white-space: nowrap;
}
th {
    position: sticky;
    top: 0;
    background: #1e1e1e;
    z-index: 3;
}
.left-sticky {
    position: sticky;
    left: 0;
    background: #1e1e1e;
    font-weight: bold;
    z-index: 2;
    border-right: 1px solid #333; /* border between first column and data */
}
.corner-cell {
    z-index: 4;
}
.tooltip {
    position: relative;
    display: inline-block;
}
.tooltip .tooltiptext {
    visibility: hidden;
    width: max-content;
    background-color: #222;
    color: #fff;
    text-align: left;
    padding: 5px;
    border-radius: 4px;
    position: absolute;
    z-index: 10;
    white-space: pre-line;
}
.tooltip:hover .tooltiptext {
    visibility: visible;
}
.passed { background-color: #4caf50; color: #fff; }
.failed { background-color: #f44336; color: #fff; }
.yellow { background-color: #ffeb3b; color: #000; }
</style>
</head>
<body>
<div class="table-container">
<table>
<tr>
<th class="corner-cell left-sticky">Test Suite</th>
"""

# Header row with dates
for d in dates_sorted:
    html += f"<th>{d}</th>"
html += "</tr>"

# Generate table rows
for project_name in sorted(projects.keys()):
    html += f'<tr><td class="left-sticky" colspan="{len(dates_sorted)+1}" style="text-align:left;font-weight:bold;">{project_name}</td></tr>'
    for suite_name in sorted(projects[project_name].keys()):
        display_suite = suite_name.replace("Test Suites/", "")
        html += f'<tr><td class="left-sticky" style="text-align:left;">{display_suite}</td>'
        suite_entries = projects[project_name][suite_name]
        entries_by_date = {e.get("end", "N/A")[:10]: e for e in suite_entries if e.get("end")}
        for d in dates_sorted:
            entry = entries_by_date.get(d)
            if entry:
                passed = entry.get("passed") or 0
                failed = entry.get("failed") or 0
                error = entry.get("error") or 0
                incomplete = entry.get("incomplete") or 0
                skipped = entry.get("skipped") or 0
                test_cases = entry.get("test_cases") or 0
                retry = entry.get("retry_count") or 0
                start = entry.get("start") or ""
                end = entry.get("end") or ""
                duration = entry.get("duration") or ""

                # Compute color
                sum_check = passed + failed + error + incomplete + skipped
                if sum_check != test_cases or passed != test_cases:
                    color_class = "failed"
                elif retry > 0:
                    color_class = "yellow"
                else:
                    color_class = "passed"

                tooltip = (f"Test Cases: {test_cases}\n"
                           f"Passed: {passed}\n"
                           f"Failed: {failed}\n"
                           f"Error: {error}\n"
                           f"Incomplete: {incomplete}\n"
                           f"Skipped: {skipped}\n"
                           f"Retry: {retry}\n"
                           f"Start: {start}\n"
                           f"End: {end}\n"
                           f"Duration: {duration}")

                html += (f'<td class="{color_class} tooltip">'
                         f'{passed}/{test_cases}'
                         f'<span class="tooltiptext">{tooltip}</span>'
                         f'<a href="../{entry["html_file"]}" target="_blank"></a>'
                         f'</td>')
            else:
                html += "<td></td>"
        html += "</tr>"

html += """
</table>
</div>
</body>
</html>
"""

# Write HTML
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Dashboard built successfully: {OUTPUT_FILE}")
