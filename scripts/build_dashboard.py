import json
import os
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"
REPORTS_DIR = "docs/reports"  # processed HTML files should be stored here

CHAR_PX = 8       # approximate px per character for width calc
MAX_CHARS = 200   # cap as requested
MIN_LEFT_PX = 220
MAX_LEFT_PX = 1200
DATE_COL_PX = 96  # fixed width for date columns (~10-12 chars)

def load_results():
    if not os.path.exists(RESULTS_FILE):
        print(f"Warning: {RESULTS_FILE} not found.")
        return []
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {RESULTS_FILE}: {e}")
        return []

def get_color(record):
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

    failed = record.get("failed")
    if failed is None:
        failed = total - passed if total else 0

    total_calc = passed + failed + errored + incomplete + skipped
    if total and total_calc != total:
        return "red"

    if total and passed == total:
        return "yellow" if retry and retry != 0 else "green"

    return "red"

def escape_html(s):
    if s is None:
        return ""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def escape_attr(s):
    return escape_html(s).replace("\n", " ").replace("\r", " ")

def build_dashboard():
    results = load_results()
    if not results:
        print("No results to build dashboard from.")
        return

    # Group: project -> suite -> date -> latest entry for that date
    grouped = defaultdict(lambda: defaultdict(dict))
    for r in results:
        project = r.get("project", "Unknown Project")
        suite = r.get("test_suite_id", "Unknown Suite")
        start = r.get("start") or r.get("end")
        if not start:
            continue
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            date_key = dt.strftime("%Y.%m.%d")
        except Exception:
            date_key = start[:10]
        existing = grouped[project][suite].get(date_key)
        compare_end = r.get("end") or r.get("start") or ""
        if not existing or compare_end > (existing.get("end") or existing.get("start") or ""):
            r["color"] = get_color(r)
            grouped[project][suite][date_key] = r

    all_dates = sorted(
        {d for proj in grouped.values() for suite in proj.values() for d in suite.keys()},
        reverse=True
    )[:365]

    if not all_dates:
        print("No dates found in results — nothing to render.")
        return

    # Determine longest display name (strip prefix) and cap
    max_len = 0
    for project in grouped:
        for suite in grouped[project]:
            display_name = suite.replace("Test Suites/", "")
            if len(display_name) > max_len:
                max_len = len(display_name)
    if max_len > MAX_CHARS:
        max_len = MAX_CHARS
    left_col_width = max(MIN_LEFT_PX, min(MAX_LEFT_PX, max_len * CHAR_PX + 24))

    # Build HTML with colgroup to fix widths exactly
    html = []
    html.append("<!doctype html>")
    html.append("<html lang='en'><head><meta charset='utf-8'><title>QA Automation Report</title>")
    html.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    html.append("<style>")
    html.append("body { background:#121212; color:#e0e0e0; font-family: Inter, Roboto, Arial, sans-serif; margin:16px; }")
    html.append("h1 { color:#fff; margin:8px 0 16px 0; }")
    html.append(".table-container { overflow-x:auto; width:100%; border:1px solid #2b2b2b; }")
    html.append("table.dashboard { border-collapse:collapse; width:max-content; min-width:100%; table-layout:fixed; }")
    # col styles will be inserted dynamically via colgroup below
    html.append("th, td { border:1px solid #2b2b2b; padding:6px 10px; text-align:center; white-space:nowrap; }")
    html.append("th { background:#202020; position:sticky; top:0; z-index:6; }")
    html.append(".project-row-right { background:#181818; color:#fff; font-weight:700; text-align:left; padding-left:12px; }")
    # sticky left column (suite name and left header/project-left)
    html.append(f".left-sticky {{ position:sticky; left:0; z-index:7; background:#111111; width:{left_col_width}px; text-align:left; padding-left:10px; overflow:hidden; text-overflow:ellipsis; }}")
    html.append(".left-sticky a { display:block; color:inherit; text-decoration:none; }")
    # date cell fixed width (applies because we use colgroup)
    html.append("td.green { background:#2e7d32; color:#fff; }")
    html.append("td.yellow { background:#f9a825; color:#000; }")
    html.append("td.red { background:#c62828; color:#fff; }")
    html.append("td.empty { background:#1b1b1b; color:#666; }")
    html.append(".cell-link { display:block; width:100%; height:100%; color:inherit; text-decoration:none; }")
    # tooltip styles
    html.append(".tooltip { position:relative; display:inline-block; }")
    html.append(".tooltip .tooltiptext { visibility:hidden; opacity:0; transition:opacity .18s; position:absolute; left:50%; transform:translateX(-50%); bottom:125%; background:#222; color:#fff; padding:8px 10px; border-radius:6px; white-space:normal; text-align:left; z-index:50; box-shadow:0 4px 10px rgba(0,0,0,0.6); width:280px; font-size:13px; }")
    html.append(".tooltip:hover .tooltiptext { visibility:visible; opacity:1; }")
    html.append(".tooltip .tooltiptext b { display:inline-block; width:90px; }")
    html.append("@media (max-width:800px){ .left-sticky{ min-width:160px; max-width:320px; } }")
    html.append("</style></head><body>")
    html.append("<h1>QA Automation Report</h1>")
    html.append("<div class='table-container'>")

    # Start table, colgroup: first column width then one col per date with fixed width
    html.append("<table class='dashboard'>")
    html.append("<colgroup>")
    html.append(f"<col style='width: {left_col_width}px;'/>")
    for _ in all_dates:
        html.append(f"<col style='width: {DATE_COL_PX}px;'/>")
    html.append("</colgroup>")

    # header row: first th sticky left, then dates
    html.append("<thead>")
    header = "<tr>"
    header += f"<th class='left-sticky'>Test Suite</th>"
    for d in all_dates:
        header += f"<th>{escape_html(d[5:])}</th>"
    header += "</tr>"
    html.append(header)
    html.append("</thead>")

    # single table body where projects are represented by a project header row
    html.append("<tbody>")
    for project in sorted(grouped.keys()):
        # Project header: make two cells so left-most project name remains sticky
        colspan = len(all_dates)
        # left sticky cell for project name
        html.append("<tr>")
        html.append(f"<td class='left-sticky'><strong>{escape_html(project)}</strong></td>")
        # right spanning cell with background acting as header across dates
        html.append(f"<td class='project-row-right' colspan='{colspan}'></td>")
        html.append("</tr>")

        for suite in sorted(grouped[project].keys()):
            display_name = suite.replace("Test Suites/", "")
            html.append("<tr>")
            # left sticky suite name
            html.append(f"<td class='left-sticky'><div>{escape_html(display_name)}</div></td>")
            # date cells
            for d in all_dates:
                entry = grouped[project][suite].get(d)
                if not entry:
                    html.append("<td class='empty'>–</td>")
                    continue

                total = entry.get("test_cases", 0) or 0
                passed = entry.get("passed", 0) or 0
                failed_display = entry.get("failed")
                if failed_display is None:
                    failed_display = total - passed if total else 0
                color = entry.get("color", "red")

                tooltip_lines = [
                    ("Test Cases", str(total)),
                    ("Passed", str(passed)),
                    ("Failed", str(failed_display)),
                    ("Error", str(entry.get("error", 0) or 0)),
                    ("Incomplete", str(entry.get("incomplete", 0) or 0)),
                    ("Skipped", str(entry.get("skipped", 0) or 0)),
                    ("Retry", str(entry.get("retry_count", 0) or 0)),
                    ("Start", entry.get("start", "–")),
                    ("End", entry.get("end", "–")),
                    ("Duration", f"{entry.get('duration', '–')} min")
                ]
                tooltip_html = "<br>".join(f"<b>{escape_html(k)}:</b> {escape_html(v)}" for k, v in tooltip_lines)

                html_file = entry.get("html_file", "")
                filename = os.path.basename(html_file) if html_file else ""
                link_href = None
                if filename:
                    candidate = os.path.join(REPORTS_DIR, filename)
                    if os.path.exists(candidate):
                        link_href = f"reports/{escape_attr(filename)}"

                display_text = f"{passed}/{failed_display}"

                if link_href:
                    cell_inner = (
                        f"<div class='tooltip'>"
                        f"<a class='cell-link' href='{escape_attr(link_href)}' target='_blank'>{escape_html(display_text)}</a>"
                        f"<div class='tooltiptext'>{tooltip_html}</div></div>"
                    )
                else:
                    cell_inner = (
                        f"<div class='tooltip'><span class='cell-link'>{escape_html(display_text)}</span>"
                        f"<div class='tooltiptext'>{tooltip_html}</div></div>"
                    )

                html.append(f"<td class='{color}'>{cell_inner}</td>")
            html.append("</tr>")
    html.append("</tbody>")
    html.append("</table></div></body></html>")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"✅ Dashboard updated: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dashboard()
