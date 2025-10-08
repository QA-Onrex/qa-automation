import json
import os
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"
REPORTS_DIR = "docs/reports"

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

def build_dashboard():
    results = load_results()
    if not results:
        print("No results to build dashboard from.")
        return

    grouped = defaultdict(lambda: defaultdict(dict))

    for r in results:
        project = r.get("project", "Unknown Project")
        suite_raw = r.get("test_suite_id", "Unknown Suite")
        suite = suite_raw
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

    # find longest test suite name, but cap at 200 characters
    max_len = 0
    for project in grouped:
        for suite in grouped[project]:
            display_name = suite.replace("Test Suites/", "")
            if len(display_name) > max_len:
                max_len = len(display_name)
    if max_len > 200:
        max_len = 200

    # estimate px width for longest name
    char_width_px = 9  # approximate monospace width
    left_col_width = max(220, min(1800, max_len * char_width_px + 24))  # safe range

    # fixed width for each date column (~10-12 characters)
    date_col_width = 100

    html_parts = [
        "<!doctype html>",
        "<html lang='en'><head><meta charset='utf-8'><title>QA Automation Report</title>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<style>",
        "body { background:#121212; color:#e0e0e0; font-family: Inter, Roboto, Arial, sans-serif; margin:16px; }",
        "h1 { color:#fff; margin:8px 0 16px 0; }",
        ".table-container { overflow-x:auto; width:100%; border:1px solid #2b2b2b; }",
        "table.dashboard { border-collapse:collapse; width:max-content; min-width:100%; table-layout:fixed; }",
        "th, td { border:1px solid #2b2b2b; padding:6px 10px; text-align:center; white-space:nowrap; }",
        "th { background:#202020; position:sticky; top:0; z-index:5; }",
        ".project-row td { background:#181818; color:#ffffff; font-weight:700; text-align:left; padding-left:12px; }",
        f".suite-name {{ position:sticky; left:0; z-index:4; background:#111111; width:{left_col_width}px; text-align:left; padding-left:10px; overflow:hidden; text-overflow:ellipsis; }}",
        f"th:not(:first-child), td:not(:first-child) {{ width:{date_col_width}px; }}",
        ".suite-name a { display:block; color:inherit; text-decoration:none; }",
        "td.green { background:#2e7d32; color:#fff; }",
        "td.yellow { background:#f9a825; color:#000; }",
        "td.red { background:#c62828; color:#fff; }",
        "td.empty { background:#1b1b1b; color:#666; }",
        ".cell-link { display:block; width:100%; height:100%; color:inherit; text-decoration:none; }",
        ".tooltip { position:relative; display:inline-block; }",
        ".tooltip .tooltiptext { visibility:hidden; opacity:0; transition:opacity .18s ease-in-out;",
        "  position:absolute; left:50%; transform:translateX(-50%); bottom:125%;",
        "  background:#222; color:#fff; padding:8px 10px; border-radius:6px; white-space:normal;",
        "  text-align:left; z-index:50; box-shadow:0 4px 10px rgba(0,0,0,0.6); width:260px; font-size:13px; }",
        ".tooltip:hover .tooltiptext { visibility:visible; opacity:1; }",
        ".tooltip .tooltiptext b { display:inline-block; width:86px; }",
        "@media (max-width:800px){ .suite-name{min-width:160px;max-width:240px;} }",
        "</style></head><body>",
        "<h1>QA Automation Report</h1>",
        "<div class='table-container'><table class='dashboard'>"
    ]

    header_row = "<tr><th>Test Suite</th>"
    for d in all_dates:
        header_row += f"<th>{d[5:]}</th>"
    header_row += "</tr>"
    html_parts.append(header_row)

    for project in sorted(grouped.keys()):
        colspan = len(all_dates) + 1
        html_parts.append(f"<tr class='project-row'><td colspan='{colspan}'>{project}</td></tr>")

        for suite in sorted(grouped[project].keys()):
            display_name = suite.replace("Test Suites/", "")
            html_parts.append("<tr>")
            html_parts.append(f"<td class='suite-name'>{escape_html(display_name)}</td>")

            for d in all_dates:
                entry = grouped[project][suite].get(d)
                if not entry:
                    html_parts.append("<td class='empty'>–</td>")
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
                link_href = f"reports/{filename}" if filename else None

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

                html_parts.append(f"<td class='{color}'>{cell_inner}</td>")

            html_parts.append("</tr>")

    html_parts.append("</table></div></body></html>")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    print(f"✅ Dashboard updated: {OUTPUT_FILE}")

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

if __name__ == "__main__":
    build_dashboard()
