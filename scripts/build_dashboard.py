import json
import os
import hashlib
from datetime import datetime
from collections import defaultdict

RESULTS_FILE = "data/results.json"
OUTPUT_FILE = "docs/index.html"  # dashboard location

def load_results():
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found.")
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_color(record):
    total = record.get("test_cases", 0) or 0
    passed = record.get("passed", 0) or 0
    failed = record.get("failed", 0) or 0
    errored = record.get("error", 0) or 0
    incomplete = record.get("incomplete", 0) or 0
    skipped = record.get("skipped", 0) or 0
    retry = record.get("retry_count", 0) or 0

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

    # Get password hash from environment
    password = os.getenv("REPORT_PASSWORD", "")
    password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
    
    if not password:
        print("::warning::REPORT_PASSWORD not set. Dashboard will have no authentication.")

    # Group data by Project → Test Suite ID → Date
    data = defaultdict(lambda: defaultdict(dict))

    for r in results:
        project = r.get("project", "Unknown")
        suite = r.get("test_suite_id", "Unknown")
        start = r.get("start") or r.get("end")
        if not start:
            continue
        date = datetime.fromisoformat(start.replace("Z", "+00:00")).strftime("%Y.%m.%d")

        # Keep only latest record for the date
        if date not in data[project][suite] or r.get("end", "") > data[project][suite][date].get("end", ""):
            r["color"] = get_color(r)
            data[project][suite][date] = r

    # Calculate maximum suite name length for adaptive column width
    max_length = 0
    for project in data:
        for suite in data[project]:
            name = suite.replace("Test Suites/", "")
            if len(name) > max_length:
                max_length = len(name)
    left_col_width = max_length * 9 + 16  # approximate pixel width

    # Collect all dates (latest first)
    all_dates = sorted(
        {d for proj in data.values() for suite in proj.values() for d in suite.keys()},
        reverse=True
    )[:365]

    # Build HTML
    html = [
        "<html><head><meta charset='utf-8'><title>QA Automation Report</title>",
        "<style>",
        "body { background-color: #1e1e1e; color: #ddd; font-family: Arial, sans-serif; margin:0; padding:0; }",
        "h1 { color: #fff; padding: 10px 0 10px 16px; margin:0; }",
        "#login-container { display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; }",
        "#login-box { background-color: #2b2b2b; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }",
        "#login-box h2 { margin-top: 0; color: #fff; }",
        "#password-input { width: 250px; padding: 10px; margin: 10px 0; background-color: #1e1e1e; border: 1px solid #444; color: #ddd; border-radius: 4px; }",
        "#login-button { padding: 10px 20px; background-color: #2e7d32; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }",
        "#login-button:hover { background-color: #1b5e20; }",
        "#error-message { color: #c62828; margin-top: 10px; display: none; }",
        "#dashboard-content { display: none; }",
        "table { border-collapse: collapse; }",
        "th, td { border: 1px solid #444; text-align: center; padding: 6px; }",
        "th { background-color: #2b2b2b; font-weight: bold; position: sticky; top: 0; z-index: 2; }",
        "th::before { content: ''; position: absolute; top: -1px; left: 0; right: 0; height: 1px; background-color: #2b2b2b; }",
        "th:first-child { position: sticky; left: 0; z-index: 4; background-color: #2b2b2b; text-align: left; padding-left: 8px; border-right: 2px solid #444; }",
        "th:first-child::before { content: ''; position: absolute; top: -1px; left: -1px; width: calc(100% + 1px); height: calc(100% + 1px); background-color: #2b2b2b; z-index: -1; }",
        "td.green { background-color: #2e7d32; color: #fff; cursor: pointer; }",
        "td.yellow { background-color: #f9a825; color: #000; cursor: pointer; }",
        "td.red { background-color: #c62828; color: #fff; cursor: pointer; }",
        "td.green:hover, td.yellow:hover, td.red:hover { opacity: 0.8; }",
        "td.empty { background-color: #2b2b2b; color: #666; }",
        "td.project-separator { background-color: #1e1e1e; }",
        f".suite-name {{ position: sticky; left: 0; background-color: #1e1e1e; width: {left_col_width}px; text-align: left; padding-left: 8px; font-weight: normal; z-index:1; border-right: 2px solid #444; }}",
        ".suite-name::before { content: ''; position: absolute; left: -1px; top: 0; width: 1px; bottom: 0; background-color: #1e1e1e; }",
        ".project-header { position: sticky; left: 0; display: table-cell; background-color: #1e1e1e; text-align: left; padding-left: 8px; font-weight: bold; z-index: 1; border-right: 2px solid #444; border-bottom: 2px solid #444; }",
        ".project-header::before { content: ''; position: absolute; left: -1px; top: 0; width: 1px; bottom: 0; background-color: #1e1e1e; }",
        ".table-container { overflow-x: auto; overflow-y: auto; max-height: 90vh; }",
        ".tooltip { position: absolute; display: none; background-color: #2b2b2b; border: 1px solid #444; padding: 10px; border-radius: 4px; z-index: 1000; pointer-events: none; white-space: nowrap; }",
        ".tooltip-row { margin: 3px 0; }",
        ".tooltip-label { font-weight: bold; display: inline-block; width: 100px; }",
        "</style>",
        "<script>",
        f"const PASSWORD_HASH = '{password_hash}';",
        "const data = " + json.dumps(data, default=str) + ";",
        "",
        "async function hashPassword(password) {",
        "  const msgBuffer = new TextEncoder().encode(password);",
        "  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);",
        "  const hashArray = Array.from(new Uint8Array(hashBuffer));",
        "  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');",
        "}",
        "",
        "async function checkPassword() {",
        "  const password = document.getElementById('password-input').value;",
        "  const hash = await hashPassword(password);",
        "  if (hash === PASSWORD_HASH) {",
        "    sessionStorage.setItem('reportPassword', password);",
        "    document.getElementById('login-container').style.display = 'none';",
        "    document.getElementById('dashboard-content').style.display = 'block';",
        "  } else {",
        "    document.getElementById('error-message').style.display = 'block';",
        "  }",
        "}",
        "",
        "document.addEventListener('DOMContentLoaded', function() {",
        "  const savedPassword = sessionStorage.getItem('reportPassword');",
        "  if (savedPassword) {",
        "    hashPassword(savedPassword).then(hash => {",
        "      if (hash === PASSWORD_HASH) {",
        "        document.getElementById('login-container').style.display = 'none';",
        "        document.getElementById('dashboard-content').style.display = 'block';",
        "      }",
        "    });",
        "  }",
        "  document.getElementById('password-input').addEventListener('keypress', function(e) {",
        "    if (e.key === 'Enter') checkPassword();",
        "  });",
        "});",
        "",
        "function showTooltip(e, project, suite, date) {",
        "  const record = data[project][suite][date];",
        "  if (!record) return;",
        "  const tooltip = document.getElementById('tooltip');",
        "  const start = new Date(record.start);",
        "  const end = new Date(record.end);",
        "  const formatDate = (d) => d.getFullYear().toString().slice(2) + '/' + ",
        "    String(d.getMonth()+1).padStart(2,'0') + '/' + String(d.getDate()).padStart(2,'0') + ' - ' +",
        "    String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');",
        "  const totalSeconds = Math.floor(record.duration * 60);",
        "  const minutes = Math.floor(totalSeconds / 60);",
        "  const seconds = totalSeconds % 60;",
        "  const durationStr = String(minutes).padStart(2,'0') + ':' + String(seconds).padStart(2,'0');",
        "  tooltip.innerHTML = `",
        "    <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${record.profile || 'N/A'}</strong></div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${record.test_cases || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${record.passed || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${record.failed || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${record.error || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Incomplete:</span>${record.incomplete || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${record.skipped || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Retry:</span>${record.retry_count || 0}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${formatDate(start)}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>End:</span>${formatDate(end)}</div>",
        "    <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>",
        "  `;",
        "  tooltip.style.display = 'block';",
        "  tooltip.style.left = (e.pageX + 10) + 'px';",
        "  tooltip.style.top = (e.pageY + 10) + 'px';",
        "}",
        "function hideTooltip() {",
        "  document.getElementById('tooltip').style.display = 'none';",
        "}",
        "function openReport(project, suite, date) {",
        "  const record = data[project][suite][date];",
        "  if (record && record.html_file) {",
        "    const path = record.html_file.replace('docs/', '');",
        "    window.open(path, '_blank');",
        "  }",
        "}",
        "</script>",
        "</head><body>",
        "<div id='login-container'>",
        "  <div id='login-box'>",
        "    <h2>QA Automation Report</h2>",
        "    <div>",
        "      <input type='password' id='password-input' placeholder='Enter password' autofocus>",
        "    </div>",
        "    <div>",
        "      <button id='login-button' onclick='checkPassword()'>Login</button>",
        "    </div>",
        "    <div id='error-message'>Incorrect password. Please try again.</div>",
        "  </div>",
        "</div>",
        "<div id='dashboard-content'>",
        "<div id='tooltip' class='tooltip'></div>",
        "<h1>QA Automation Report</h1>",
        "<div class='table-container'>",
        "<table>",
        "<tr><th>Test Suite</th>" + "".join(f"<th>{d[5:]}</th>" for d in all_dates) + "</tr>"
    ]

    # Flatten all projects and suites into single table
    for project in sorted(data.keys()):
        html.append(f"<tr><td class='project-header'>{project}</td>" + "<td class='project-separator'></td>" * len(all_dates) + "</tr>")
        for suite in sorted(data[project].keys()):
            display_name = suite.replace("Test Suites/", "")
            html.append(f"<tr><td class='suite-name'>{display_name}</td>")
            for date in all_dates:
                if date in data[project][suite]:
                    record = data[project][suite][date]
                    color = record["color"]
                    passed = record.get("passed", 0)
                    total = record.get("test_cases", 0)
                    failed = total - passed if total else 0
                    html.append(f"<td class='{color}' onmousemove='showTooltip(event, \"{project}\", \"{suite}\", \"{date}\")' onmouseleave='hideTooltip()' onclick='openReport(\"{project}\", \"{suite}\", \"{date}\")'>{passed}/{failed}</td>")
                else:
                    html.append("<td class='empty'>–</td>")
            html.append("</tr>")

    html.append("</table>")
    html.append("</div>")  # close table-container
    html.append("</div>")  # close dashboard-content
    html.append("</body></html>")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"✅ Dashboard built successfully: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dashboard()
