import csv
from html import escape

from config.settings import CSV_FILE, EXPORT_DIR, HTML_FILE


def export_jobs(rows) -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company", "title", "location", "source", "score", "url",
        "status", "applied", "applied_date", "notes",
    ]

    with CSV_FILE.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fieldnames})

    cards = []
    for row in rows:
        cards.append(
            f"""
            <article class="job">
                <div class="score">{row['score']}</div>
                <div class="content">
                    <h2>{escape(row['title'])}</h2>
                    <p><strong>{escape(row['company'])}</strong></p>
                    <p>{escape(row['location'])} · {escape(row['source'])}</p>
                    <a href="{escape(row['url'], quote=True)}" target="_blank" rel="noopener">Open application</a>
                </div>
            </article>
            """
        )

    HTML_FILE.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VOCANTA Shortlist</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1000px;margin:32px auto;padding:0 18px;background:#f5f7fb;color:#111827}}
h1{{margin-bottom:6px}} .meta{{color:#4b5563;margin-bottom:24px}}
.job{{display:flex;gap:18px;background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;margin:14px 0;box-shadow:0 3px 12px rgba(0,0,0,.05)}}
.score{{min-width:58px;height:58px;border-radius:50%;display:grid;place-items:center;font-size:22px;font-weight:700;background:#111827;color:white}}
h2{{margin:0 0 8px;font-size:20px}} p{{margin:6px 0;color:#374151}}
a{{display:inline-block;margin-top:10px;padding:10px 14px;border-radius:8px;background:#111827;color:white;text-decoration:none}}
</style>
</head>
<body>
<h1>VOCANTA Shortlisted Jobs</h1>
<p class="meta">{len(cards)} ranked opportunities</p>
{''.join(cards)}
</body>
</html>""",
        encoding="utf-8",
    )
