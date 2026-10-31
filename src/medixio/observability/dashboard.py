"""Single self-contained HTML page; no external assets so it works offline."""

import html
from datetime import UTC, datetime
from typing import Any

from medixio.shared.time import to_local


_COLORS = {"ok": "#1a7f37", "warn": "#9a6700", "fail": "#cf222e"}


def _ts(ts: float) -> str:
    return to_local(datetime.fromtimestamp(ts, UTC)).strftime("%Y-%m-%d %H:%M:%S")


def render(status: dict[str, Any], metrics: dict[str, Any], events: list[Any]) -> str:
    e = html.escape
    checks = "".join(
        f"<tr><td><span class='pill' style='background:{_COLORS[c['status']]}'>"
        f"{c['status']}</span></td><td>{e(c['name'])}</td><td>{e(c['detail'])}</td></tr>"
        for c in status["checks"]
    )
    metric_rows = (
        "".join(
            f"<tr><td>{e(name)}</td><td>{m['count']}</td><td>{m['failed']}</td>"
            f"<td>{m['avg']}</td><td>{m['max']}</td><td>{m['total']}</td></tr>"
            for name, m in metrics.items()
        )
        or "<tr><td colspan=6>No metrics yet</td></tr>"
    )
    event_rows = (
        "".join(
            f"<tr><td>{_ts(ev['ts'])}</td><td>{e(ev['level'])}</td><td>{e(ev['logger'])}</td>"
            f"<td>{e(ev['message'])}"
            + (
                f"<details><summary>{e(ev['exc_type'] or 'traceback')}</summary>"
                f"<pre>{e(ev['traceback'])}</pre></details>"
                if ev["traceback"]
                else ""
            )
            + "</td></tr>"
            for ev in events
        )
        or "<tr><td colspan=4>No warnings or errors</td></tr>"
    )
    overall = status["status"]
    badge = f"<span class='pill' style='background:{_COLORS[overall]}'>{overall}</span>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>Medixio status</title>
<style>
:root {{ --bg:#fff; --fg:#1f2328; --muted:#656d76; --line:#d0d7de; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#8d96a0; --line:#30363d; }}
}}
body {{ background:var(--bg); color:var(--fg); font:14px system-ui,sans-serif;
       margin:0 auto; max-width:1100px; padding:16px; }}
h1 {{ font-size:20px; }} h2 {{ font-size:16px; margin-top:28px; }}
table {{ border-collapse:collapse; width:100%; }}
td,th {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left;
        vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; }}
.pill {{ color:#fff; border-radius:10px; padding:1px 8px; font-size:12px; }}
pre {{ white-space:pre-wrap; font-size:12px; overflow-x:auto; }}
.wrap {{ overflow-x:auto; }}
</style></head><body>
<h1>Medixio {badge}</h1>
<p style="color:var(--muted)">Auto-refresh 30 s · times in Bogotá</p>
<h2>Checks</h2><div class="wrap"><table>
<tr><th></th><th>Check</th><th>Detail</th></tr>{checks}</table></div>
<h2>Metrics, last 24 h</h2><div class="wrap"><table>
<tr><th>Name</th><th>Count</th><th>Failed</th><th>Avg</th><th>Max</th><th>Total</th></tr>
{metric_rows}</table></div>
<h2>Recent warnings and errors</h2><div class="wrap"><table>
<tr><th>Time</th><th>Level</th><th>Logger</th><th>Message</th></tr>{event_rows}
</table></div>
</body></html>"""
