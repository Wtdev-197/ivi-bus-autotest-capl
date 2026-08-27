from datetime import datetime
from html import escape
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
REPORT_FILE = RESULTS_DIR / "test_report.html"

STATUS_MAP = {
    "passed": "通过",
    "failed": "失败",
    "broken": "错误",
    "skipped": "跳过",
}

rows = []

for result_file in RESULTS_DIR.glob("*-result.json"):
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        continue

    timestamp = data.get("start")
    test_time = "-"
    if timestamp:
        test_time = datetime.fromtimestamp(
            timestamp / 1000
        ).strftime("%Y-%m-%d %H:%M:%S")

    status = str(data.get("status", "unknown"))
    name = str(data.get("name", "-"))

    rows.append(
        f"<tr><td>{escape(name)}</td>"
        f"<td class='status-{escape(status)}'>"
        f"{escape(STATUS_MAP.get(status, status))}</td>"
        f"<td>{test_time}</td></tr>"
    )

if not rows:
    rows.append("<tr><td colspan='3'>暂无测试结果</td></tr>")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>测试报告</title>
<style>
body {{ font-family: "Microsoft YaHei", Arial; margin: 30px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 10px; }}
th {{ background: #f2f2f2; }}
.status-passed {{ color: green; font-weight: bold; }}
.status-failed, .status-broken {{ color: red; font-weight: bold; }}
.status-skipped {{ color: orange; font-weight: bold; }}
</style>
</head>
<body>
<h2>测试报告</h2>
<table>
<thead>
<tr><th>测试用例名称</th><th>结果</th><th>时间</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>
"""

REPORT_FILE.write_text(html, encoding="utf-8")
print(f"测试报告已生成：{REPORT_FILE}")
