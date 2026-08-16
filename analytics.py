from html import escape

from rich.console import Console
from rich.table import Table

from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database
from core.follow_up_store import follow_up_statistics
from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response

ANALYTICS_FILE=EXPORT_DIR/"analytics.html"


def response_actions(connection):
    try: rows=connection.execute("SELECT er.classification,er.confidence,er.reason,er.sender,er.subject,er.received_at,j.company,j.title FROM employer_responses er JOIN jobs j ON j.id=er.job_id ORDER BY er.received_at DESC LIMIT 25").fetchall()
    except Exception: return []
    items=[]
    for row in rows:
        response=EmployerResponse(str(row[0]),int(row[1]),str(row[2])); action=action_for_response(response); items.append({"priority":action.priority,"action":action.action,"sender":str(row[3]),"subject":str(row[4]),"received_at":str(row[5]),"company":str(row[6]),"title":str(row[7]),"classification":response.status})
    order={"URGENT":0,"HIGH":1,"MEDIUM":2,"LOW":3}; return sorted(items,key=lambda item:(order.get(item['priority'],9),item['received_at']))


def pending_reply_drafts(connection):
    try: rows=connection.execute("SELECT d.message_id,d.subject,d.body,d.created_at,j.company,j.title FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='AWAITING_APPROVAL' ORDER BY d.created_at DESC").fetchall()
    except Exception: return []
    return [{"message_id":str(r[0]),"subject":str(r[1]),"body":str(r[2]),"created_at":str(r[3]),"company":str(r[4]),"title":str(r[5])} for r in rows]


def build_html(data,due_rows,follow_stats=None,actions=None,drafts=None):
    EXPORT_DIR.mkdir(parents=True,exist_ok=True); follow_stats=follow_stats or {}; actions=actions or []; drafts=drafts or []
    follow_cards="".join(f"<article><h3>{escape(r['title'])}</h3><p><strong>{escape(r['company'])}</strong></p><p>Due: {escape(r['follow_up_date'] or '')}</p></article>" for r in due_rows)
    action_cards="".join(f"<article><h3>{escape(i['priority'])}: {escape(i['action'])}</h3><p><strong>{escape(i['company'])}</strong> · {escape(i['title'])}</p><p>{escape(i['classification'])} · {escape(i['subject'])}</p></article>" for i in actions)
    draft_cards="".join(f"<article><h3>Approval required: {escape(d['company'])}</h3><p><strong>{escape(d['subject'])}</strong></p><pre>{escape(d['body'])}</pre><form method='post' action='/approve'><input type='hidden' name='message_id' value='{escape(d['message_id'],quote=True)}'><button type='submit'>Approve reply</button></form></article>" for d in drafts)
    health="".join(f'<div class="card"><div class="value">{follow_stats.get(k,0)}</div><div class="label">Follow up {label}</div></div>' for k,label in [('pending','pending'),('completed','sent'),('failed','failed'),('cancelled','cancelled')])
    ANALYTICS_FILE.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{APP_DISPLAY_NAME} Analytics</title><style>body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;padding:0 18px;background:#f5f7fb;color:#111827}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}.card,article{{background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;margin:10px 0}}.value{{font-size:30px;font-weight:700}}pre{{white-space:pre-wrap;font-family:inherit}}button{{padding:10px 16px;font-weight:700;cursor:pointer}}</style></head><body><h1>{APP_DISPLAY_NAME} Pipeline Analytics</h1><div class="grid"><div class="card"><div class="value">{data['shortlisted']}</div><div>Shortlisted</div></div><div class="card"><div class="value">{data['applied']}</div><div>Applications</div></div><div class="card"><div class="value">{data['interviews']}</div><div>Interviews</div></div><div class="card"><div class="value">{data['offers']}</div><div>Offers</div></div><div class="card"><div class="value">{len(drafts)}</div><div>Replies awaiting approval</div></div>{health}</div><section><h2>Reply approvals</h2>{draft_cards or '<p>No replies awaiting approval.</p>'}</section><section><h2>Employer actions</h2>{action_cards or '<p>No employer actions need attention.</p>'}</section><section><h2>Follow ups due</h2>{follow_cards or '<p>No follow ups are due.</p>'}</section></body></html>""",encoding="utf8")


def main():
    console=Console(); database=Database()
    try:
        data=database.analytics(SHORTLIST_SCORE); due=database.list_due_follow_ups(); stats=follow_up_statistics(database.connection); actions=response_actions(database.connection); drafts=pending_reply_drafts(database.connection)
        table=Table(title=f"{APP_DISPLAY_NAME} Pipeline Analytics"); table.add_column("Metric"); table.add_column("Value",justify="right")
        for label,value in [("Shortlisted",data['shortlisted']),("Applications",data['applied']),("Interviews",data['interviews']),("Offers",data['offers']),("Replies awaiting approval",len(drafts)),("Employer actions",len(actions))]: table.add_row(label,str(value))
        console.print(table); build_html(data,due,stats,actions,drafts); return 0
    finally: database.close()


if __name__=="__main__": raise SystemExit(main())
