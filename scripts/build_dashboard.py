import json
import os
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"
REPORTS_DIR = "docs/reports"

# Visual sizing config
CHAR_PX = 8        # approx px per character for the left column width calc
MAX_CHARS = 200    # cap characters
MIN_LEFT_PX = 220
MAX_LEFT_PX = 1200
DATE_COL_PX = 96   # fixed width for each date column (approx 10-12 chars)
HEADER_HEIGHT_PX = 48  # fixed header height used for sticky offsets
MAX_DAYS = 365

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

    # Group results by project -> suite -> date -> latest record for that date
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

    # Collect all dates (latest first)
    all_dates = sorted(
        {d for proj in grouped.values() for suite in proj.values() for d in suite.keys()},
        reverse=True
    )[:MAX_DAYS]

    if not all_dates:
        print("No dates found in results — nothing to render.")
        return

    # Determine longest suite display name (strip prefix) and cap by MAX_CHARS
    max_len = 0
    for project in grouped:
        for suite in grouped[project]:
            display_name = suite.replace("Test Suites/", "")
            if len(display_name) > max_len:
                max_len = len(display_name)
    if max_len > MAX_CHARS:
        max_len = MAX_CHARS

    left_col_width = max(MIN_LEFT_PX, min(MAX_LEFT_PX, max_len * CHAR_PX + 24))

    # Build HTML
    parts = []
    parts.append("<!doctype html>")
    parts.append("<html lang='en'><head><meta charset='utf-8'><title>QA Automation Report</title>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    parts.append("<style>")
    parts.append(f"""
/* Page reset */
html, body {{
  height: 100%;
  margin: 0;
  padding: 0;
  background: #121212;
  color: #e0e0e0;
  font-family: Inter, Roboto, Arial, sans-serif;
}}

/* Page padding so content isn't glued to viewport */
.page-wrapper {{
  padding: 16px;
  box-sizing: border-box;
}}

/* Container that handles both scrollbars.
   scrollbar-gutter: stable ensures vertical scrollbar space is always reserved (avoids 1-2px jump). */
.table-container {{
  overflow: auto;
  width: 100%;
  max-height: 85vh;          /* vertical scroll inside container */
  border: 1px solid #2b2b2b;
  box-sizing: border-box;
  scrollbar-gutter: stable both-edges;
  background: #0f0f0f;
}}

/* Table layout fixed so col widths are exact and stable */
table.dashboard {{
  border-collapse: collapse;
  border-spacing: 0;
  width: max-content;
  min-width: 100%;
  table-layout: fixed;
  margin: 0;
}}

/* Columns and cells */
col.left-col {{ width: {left_col_width}px; }}
col.date-col {{ width: {DATE_COL_PX}px; }}
th, td {{
  border: 1px solid #2b2b2b;
  padding: 6px 10px;
  text-align: center;
  white-space: nowrap;
  box-sizing: border-box;
}}
/* Header (dates) sticky at top of the scrolling container */
thead th {{
  position: sticky;
  top: 0;
  height: {HEADER_HEIGHT_PX}px;
  line-height: {HEADER_HEIGHT_PX}px;
  background: #202020;
  z-index: 14;
  margin: 0;
}}

/* Top-left corner: sticky both top and left */
th.corner {{
  position: sticky;
  top: 0;
  left: 0;
  z-index: 18;
  background: #202020;
  text-align: left;
  padding-left: 12px;
}}

/* Left sticky cells (suite names, project-left cell) — they sit below header,
   so they use top offset = HEADER_HEIGHT_PX to avoid overlap. */
.left-sticky {{
  position: sticky;
  left: 0;
  top: {HEADER_HEIGHT_PX}px;
  z-index: 13;
  background: #111111;
  text-align: left;
  padding-left: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
}}

/* Project header right cell uses background and spans dates; keep it behind header */
.project-row-right {{
  background: #181818;
  color: #fff;
  font-weight: 700;
  text-align: left;
  padding-left: 12px;
}}

/* Colors for result cells */
td.green {{ background: #2e7d32; color: #fff; }}
td.yellow {{ background: #f9a825; color: #000; }}
td.red {{ background: #c62828; color: #fff; }}
td.empty {{ background: #0f0f0f; color: #666; }}

/* Make link fill the cell */
.cell-link {{ display:block; width:100%; height:100%; color:inherit; text-decoration:none; }}

/* Tooltip */
.tooltip {{ position: relative; display: inline-block; }}
.tooltip .tooltiptext {{
  visibility: hidden; opacity: 0; transition: opacity .18s;
  position: absolute; left: 50%; transform: translateX(-50%); bottom: 125%;
  background: #222; color: #fff; padding: 8px 10px; border-radius: 6px;
  white-space: normal; text-align: left; z-index: 50; box-shadow: 0 4px 10px rgba(0,0,0,0.6);
  width: 320px; font-size: 13px;
}}
.tooltip:hover .tooltiptext {{ visibility: visible; opacity: 1; }}
.tooltip .tooltiptext b {{ display: inline-block; width: 95px; }}

/* Responsive adjustments */
@media (max-width: 800px) {{
  .left-sticky {{ min-width: 160px; max-width: 320px; }}
}}
""")
    parts.append("</style></head><body>")
    parts.append("<div class='page-wrapper'>")
    parts.append("<h1>QA Automation Report</h1>")
    parts.append("<div class='table-container'>")

    # Colgroup: first col fixed, then date columns fixed
    parts.append("<table class='dashboard'>")
    parts.append("<colgroup>")
    parts.append("<col class='left-col'/>")
    for _ in all_dates:
        parts.append("<col class='date-col'/>")
    parts.append("</colgroup>")

    # Header (thead) with corner cell sticky top+left and date headers sticky top
    parts.append("<thead><tr>")
    parts.append("<th class='corner'>Test Suite</th>")
    for d in all_dates:
        parts.append(f"<th>{escape_html(d[5:])}</th>")
    parts.append("</tr></thead>")

    # Body: single table
    parts.append("<tbody>")
    for project in sorted(grouped.keys()):
        # Project header: left sticky cell with project name, right cell spans dates (acts as separator)
        colspan = len(all_dates)
        parts.append("<tr>")
        parts.append(f"<td class='left-sticky'><strong>{escape_html(project)}</strong></td>")
        parts.append(f"<td class='project-row-right' colspan='{colspan}'></td>")
        parts.append("</tr>")

        for suite in sorted(grouped[project].keys()):
            display_name = suite.replace("Test Suites/", "")
            parts.append("<tr>")
            # left sticky suite name (will remain visible while horizontally scrolling)
            parts.append(f"<td class='left-sticky'>{escape_html(display_name)}</td>")

            for d in all_dates:
                entry = grouped[project][suite].get(d)
                if not entry:
                    parts.append("<td class='empty'>–</td>")
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
                    ("Retries", str(entry.get("retry_count", 0) or 0)),
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

                parts.append(f"<td class='{color}'>{cell_inner}</td>")

            parts.append("</tr>")
    parts.append("</tbody></table></div></div></body></html>")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    print(f"✅ Dashboard updated: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dashboard()
