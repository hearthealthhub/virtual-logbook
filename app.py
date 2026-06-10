#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "logbook.json"
HTML_PATH = ROOT / "index.html"
TIMEZONE = ZoneInfo("Africa/Johannesburg")
UTC = ZoneInfo("UTC")

AERODROME_CODES = {
    "grand central": "FAGC",
    "fagc": "FAGC",
    "lanseria": "FALA",
    "fala": "FALA",
    "or tambo": "FAOR",
    "o r tambo": "FAOR",
    "faor": "FAOR",
    "rand": "FAGM",
    "fagm": "FAGM",
    "wonderboom": "FAWB",
    "fawb": "FAWB",
    "midrand": "FAGC",
    "turffontein": "FATA",
    "fata": "FATA",
}


def load_db() -> dict:
    if not DB_PATH.exists():
        return {
            "meta": {
                "owner": "Bamz",
                "role": "Helicopter Pilot",
                "timezone": "Africa/Johannesburg",
                "base_total_minutes": 7200,
                "base_total_hours_display": "120:00",
                "last_updated": None,
            },
            "entries": [],
        }
    return json.loads(DB_PATH.read_text())


def save_db(db: dict) -> None:
    DB_PATH.write_text(json.dumps(db, indent=2))


def write_site_meta() -> None:
    site_meta = ROOT / ".netlify-site.json"
    if not site_meta.exists():
        site_meta.write_text(json.dumps({"site_id": "645d6a39-6dc7-4b6a-af91-903f32f084a6", "url": "https://bamz-virtual-logbook.netlify.app"}, indent=2))


def minutes_to_display(total_minutes: int) -> str:
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def parse_duration(value: str) -> int:
    value = value.strip().lower()
    if ":" in value:
        hours, minutes = value.split(":", 1)
        return int(hours) * 60 + int(minutes)
    cleaned = value.replace("hrs", "h").replace("hr", "h").replace("hours", "h").replace("hour", "h").replace("mins", "m").replace("min", "m").replace("minutes", "m").replace("minute", "m").replace(" ", "")
    hours = minutes = 0
    if "h" in cleaned:
        before, cleaned = cleaned.split("h", 1)
        hours = int(before or 0)
    if cleaned.endswith("m"):
        minutes = int(cleaned[:-1] or 0)
    elif cleaned:
        minutes = int(cleaned)
    return hours * 60 + minutes


def parse_local_time(date_str: str, hhmm: str) -> datetime:
    hhmm = hhmm.strip().replace(":", "")
    local_dt = datetime.strptime(f"{date_str} {hhmm}", "%Y-%m-%d %H%M")
    return local_dt.replace(tzinfo=TIMEZONE)


def to_utc_hhmm(local_dt: datetime) -> str:
    return local_dt.astimezone(UTC).strftime("%H%M")


def resolve_aerodrome(value: str) -> str:
    key = value.strip().lower()
    return AERODROME_CODES.get(key, value.strip().upper())


def render_html(db: dict) -> None:
    meta = db["meta"]
    entries = list(db["entries"])
    rows = []
    for e in entries:
        rows.append(
            f"<tr><td>{e['date']}</td><td>{e['aircraft_type']}</td><td>{e['registration']}</td><td>{e['engine_type']}</td>"
            f"<td>{e['pic_name']}</td><td>{e['copilot']}</td><td>{e['from']}</td><td>{e['to']}</td>"
            f"<td>{e['departure_utc']}</td><td>{e['arrival_utc']}</td><td>{e['duration_display']}</td><td>{e['dual']}</td><td>{e['pic']}</td>"
            f"<td>{e['remarks']}</td><td>{e['running_total']}</td></tr>"
        )
    table_rows = "\n".join(rows) if rows else '<tr><td colspan="15">No entries yet.</td></tr>'
    by_day = defaultdict(int)
    by_type = defaultdict(int)
    for e in entries:
        by_day[e['date']] += e['duration_minutes']
        by_type[e['aircraft_type']] += e['duration_minutes']
    summary_rows = "".join(
        f"<tr><td>{day}</td><td>{minutes_to_display(minutes)}</td></tr>" for day, minutes in sorted(by_day.items(), reverse=True)
    ) or '<tr><td colspan="2">No flights logged yet.</td></tr>'
    type_rows = "".join(
        f"<tr><td>{aircraft_type or 'UNKNOWN'}</td><td>{minutes_to_display(minutes)}</td></tr>" for aircraft_type, minutes in sorted(by_type.items())
    ) or '<tr><td colspan="2">No aircraft totals yet.</td></tr>'
    html = f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Virtual Logbook</title>
<style>
body {{ font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
.card {{ background:#111827; border:1px solid #334155; border-radius:16px; padding:20px; margin-bottom:20px; }}
h1,h2 {{ margin-top:0; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th,td {{ border:1px solid #334155; padding:8px; text-align:left; vertical-align:top; }}
th {{ background:#1e293b; }}
.small {{ color:#94a3b8; font-size:13px; }}
</style>
</head>
<body>
<div class=\"card\">
<h1>Virtual Logbook</h1>
<p><strong>Owner:</strong> {meta['owner']}</p>
<p><strong>Timezone:</strong> {meta['timezone']}</p>
<p><strong>Total Flight Time:</strong> {minutes_to_display(meta['base_total_minutes'] + sum(e['duration_minutes'] for e in entries))}</p>
<p class=\"small\">Last updated: {meta['last_updated'] or 'Not updated yet'}</p>
</div>
<div class=\"card\">
<h2>Daily Summary</h2>
<table>
<tr><th>Date</th><th>Flight Time</th></tr>
{summary_rows}
</table>
</div>
<div class=\"card\">
<h2>Total Hours by Aircraft Type</h2>
<table>
<tr><th>Aircraft Type</th><th>Total Hours On Type</th></tr>
{type_rows}
</table>
</div>
<div class=\"card\">
<h2>Entries</h2>
<table>
<tr><th>Date</th><th>Aircraft Type</th><th>Registration</th><th>Engine Type</th><th>PIC</th><th>Copilot</th><th>From</th><th>To</th><th>DEP UTC</th><th>ARR UTC</th><th>Duration</th><th>Dual</th><th>PIC Time</th><th>Remarks</th><th>Running Total</th></tr>
{table_rows}
</table>
</div>
</body>
</html>"""
    HTML_PATH.write_text(html)


def add_entry(args: argparse.Namespace) -> dict:
    db = load_db()
    entries = db["entries"]
    duration_minutes = parse_duration(args.duration)
    departure_local = parse_local_time(args.date, args.departure_local)
    arrival_local = parse_local_time(args.date, args.arrival_local)
    if arrival_local < departure_local:
        arrival_local += timedelta(days=1)
    computed_minutes = int((arrival_local - departure_local).total_seconds() // 60)
    if computed_minutes != duration_minutes:
        duration_minutes = computed_minutes
    role = args.role.lower()
    dual = minutes_to_display(duration_minutes) if role == "copilot" else ""
    pic_time = minutes_to_display(duration_minutes) if role == "pic" else ""
    running_minutes = db["meta"]["base_total_minutes"] + sum(e["duration_minutes"] for e in entries) + duration_minutes
    entry = {
        "date": args.date,
        "aircraft_type": args.aircraft_type,
        "registration": args.registration,
        "engine_type": args.engine_type,
        "pic_name": args.pic_name,
        "copilot": "Self" if role == "copilot" else (args.copilot_name or ""),
        "from": resolve_aerodrome(args.from_aerodrome),
        "to": resolve_aerodrome(args.to_aerodrome),
        "departure_local": args.departure_local,
        "arrival_local": args.arrival_local,
        "departure_utc": to_utc_hhmm(departure_local),
        "arrival_utc": to_utc_hhmm(arrival_local),
        "duration_minutes": duration_minutes,
        "duration_display": minutes_to_display(duration_minutes),
        "dual": dual,
        "pic": pic_time,
        "remarks": args.remarks,
        "running_total": minutes_to_display(running_minutes),
        "instructor": args.instructor or "",
        "role": role,
    }
    entries.append(entry)
    db["meta"]["last_updated"] = datetime.now(tz=UTC).isoformat()
    save_db(db)
    render_html(db)
    write_site_meta()
    return entry


def summary_for_date(date_str: str) -> str:
    db = load_db()
    matches = [e for e in db["entries"] if e["date"] == date_str]
    if not matches:
        return f"No logbook entry for {date_str}."
    total = sum(e["duration_minutes"] for e in matches)
    lines = [f"{date_str}: {len(matches)} flight(s), {minutes_to_display(total)} total"]
    for e in matches:
        lines.append(
            f"- {e['aircraft_type']} {e['registration']} {e['from']}->{e['to']} {e['departure_utc']}-{e['arrival_utc']} UTC, {e['duration_display']}, remarks: {e['remarks']}"
        )
    return "\n".join(lines)


def check_today() -> int:
    today = datetime.now(tz=TIMEZONE).strftime("%Y-%m-%d")
    db = load_db()
    matches = [e for e in db["entries"] if e["date"] == today]
    if matches:
        print(summary_for_date(today))
        return 0
    print(f"No logbook entry recorded yet for {today}. Please send today\'s flight information or confirm you did not fly.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Virtual logbook manager")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add a flight entry")
    add.add_argument("--date", required=True, help="Flight date in YYYY-MM-DD")
    add.add_argument("--aircraft-type", required=True)
    add.add_argument("--registration", required=True)
    add.add_argument("--engine-type", required=True)
    add.add_argument("--pic-name", required=True)
    add.add_argument("--role", required=True, choices=["pic", "copilot"])
    add.add_argument("--copilot-name")
    add.add_argument("--from-aerodrome", required=True)
    add.add_argument("--to-aerodrome", required=True)
    add.add_argument("--departure-local", required=True, help="Local time HHMM or HH:MM")
    add.add_argument("--arrival-local", required=True, help="Local time HHMM or HH:MM")
    add.add_argument("--duration", required=True, help="Duration HH:MM or 1h20m")
    add.add_argument("--remarks", required=True)
    add.add_argument("--instructor")

    summary = sub.add_parser("summary", help="Show daily summary")
    summary.add_argument("--date", required=True)

    sub.add_parser("render", help="Render HTML view")
    sub.add_parser("check-today", help="Check whether today has been updated")
    sub.add_parser("site-meta", help="Ensure hosted site metadata exists")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "add":
        entry = add_entry(args)
        print(json.dumps(entry, indent=2))
    elif args.command == "summary":
        print(summary_for_date(args.date))
    elif args.command == "render":
        render_html(load_db())
        write_site_meta()
        print(str(HTML_PATH))
    elif args.command == "check-today":
        raise SystemExit(check_today())
    elif args.command == "site-meta":
        write_site_meta()
        print(str(ROOT / '.netlify-site.json'))


if __name__ == "__main__":
    main()
