import csv
from datetime import datetime, timezone
from html import escape

from config.settings import (
    APPLICATIONS_CSV_FILE,
    APPLICATIONS_HTML_FILE,
    EXPORT_DIR,
)


def _days_since(value: str | None) -> str:
    if not value:
        return ""
    try:
        applied = datetime.fromisoformat(value)
        return str(max(0, (datetime.now(timezone.utc) - applied).days))
    except ValueError:
        return ""


def export_applications(rows) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id", "company", "title", "location", "source", "score", "url",
        "status", "applied", "applied_date", "follow_up_date", "notes",
        "days_since_application",
    ]
    with APPLICATIONS_CSV_FILE.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            record = {name: row[name] for name in fieldnames if name != "days_since_application"}
            record["days_since_application"] = _days_since(row["applied_date"])
            writer.writerow(record)

    cards = []
    for row in rows:
        cards.append(
            f"""
            <article class="application">
                <div class="status">{escape(row['status'])}</div>
                <div class="content">
                    <h2>{escape(row['title'])}</h2>
                    <p><strong>{escape(row['company'])}</strong></p>
                    <p>{escape(row['location'])} · Score {row['score']}</p>
                    <p><strong>Applied:</strong> {escape(row['applied_date'] or 'Not applied')}</p>
                    <p><strong>Follow up:</strong> {escape(row['follow_up_date'] or 'Not set')}</p>
                    <p><strong>Days since application:</strong> {_days_since(row['applied_date']) or 'N/A'}</p>
                    <p><strong>Notes:</strong> {escape(row['notes'] or 'No notes')}</p>
                    <a href="{escape(row['url'], quote=True)}" target="_blank" rel="noopener">Open job</a>
                </div>
            </article>
            """
        )

    APPLICATIONS_HTML_FILE.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VOCANTA Applications</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1000px;margin:32px auto;padding:0 18px;background:#f5f7fb;color:#111827}}
.application{{display:flex;gap:18px;background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;margin:14px 0;box-shadow:0 3px 12px rgba(0,0,0,.05)}}
.status{{min-width:110px;font-weight:700}}
h2{{margin:0 0 8px}} p{{margin:6px 0;color:#374151}}
a{{display:inline-block;margin-top:10px;padding:10px 14px;border-radius:8px;background:#111827;color:white;text-decoration:none}}
</style>
</head>
<body>
<h1>VOCANTA Application Tracker</h1>
<p>{len(cards)} tracked applications</p>
{''.join(cards)}
</body>
</html>""",
        encoding="utf-8",
    )
