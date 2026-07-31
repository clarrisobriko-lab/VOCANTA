from rich.console import Console
from rich.table import Table
from core.database import Database

def main() -> int:
    console=Console(); db=Database()
    try:
        raw=input("Minimum score, Enter for 0: ").strip(); minimum=int(raw) if raw else 0
        company=input("Company contains, optional: ").strip().lower()
        status=input("Status, optional: ").strip().upper()
        location=input("Location contains, optional: ").strip().lower()
        rows=[]
        for row in db.list_jobs(minimum_score=minimum):
            if company and company not in row['company'].lower(): continue
            if status and status != row['status']: continue
            if location and location not in row['location'].lower(): continue
            rows.append(row)
        t=Table(title=f"VOCANTA Filtered Jobs · {len(rows)} results")
        for name in ['ID','Score','Company','Title','Location','Status']: t.add_column(name,justify='right' if name in {'ID','Score'} else 'left')
        for r in rows:t.add_row(str(r['id']),str(r['score']),r['company'],r['title'],r['location'],r['status'])
        console.print(t); return 0
    finally: db.close()

if __name__ == "__main__": raise SystemExit(main())
