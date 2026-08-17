from html import escape
from rich.console import Console
from rich.table import Table
from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database
from core.follow_up_store import follow_up_statistics
from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response
ANALYTICS_FILE=EXPORT_DIR/"analytics.html"

def _matches(item,query):
    query=(query or '').strip().casefold()
    if not query: return True
    return query in ' '.join(str(value) for value in item.values()).casefold()

def filter_records(records,query=''):
    return [item for item in records if _matches(item,query)]

def response_actions(connection):
    try: rows=connection.execute("SELECT er.classification,er.confidence,er.reason,er.sender,er.subject,er.received_at,j.company,j.title FROM employer_responses er JOIN jobs j ON j.id=er.job_id ORDER BY er.received_at DESC LIMIT 25").fetchall()
    except Exception: return []
    items=[]
    for row in rows:
        response=EmployerResponse(str(row[0]),int(row[1]),str(row[2])); action=action_for_response(response); items.append({"priority":action.priority,"action":action.action,"company":str(row[6]),"title":str(row[7]),"classification":response.status,"subject":str(row[4])})
    order={"URGENT":0,"HIGH":1,"MEDIUM":2,"LOW":3}; return sorted(items,key=lambda item:order.get(item['priority'],9))

def reply_drafts(connection,status):
    try: rows=connection.execute("SELECT d.message_id,d.subject,d.body,d.created_at,j.company,j.title FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status=? AND d.archived_at IS NULL ORDER BY d.created_at DESC",(status,)).fetchall()
    except Exception: return []
    return [{"message_id":str(r[0]),"subject":str(r[1]),"body":str(r[2]),"created_at":str(r[3]),"company":str(r[4]),"title":str(r[5])} for r in rows]

def delivered_replies(connection,limit=25,archived=False):
    clause='IS NOT NULL' if archived else 'IS NULL'
    try: rows=connection.execute(f"SELECT d.message_id,d.subject,d.sent_at,d.gmail_sent_message_id,d.archived_at,j.company,j.title FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='SENT' AND d.archived_at {clause} ORDER BY COALESCE(d.archived_at,d.sent_at) DESC LIMIT ?",(limit,)).fetchall()
    except Exception: return []
    return [{"message_id":str(r[0]),"subject":str(r[1]),"sent_at":str(r[2] or ''),"gmail_message_id":str(r[3] or ''),"archived_at":str(r[4] or ''),"company":str(r[5]),"title":str(r[6]),"delivery_status":"Gmail accepted" if r[3] else "Sent"} for r in rows]

def reply_audit(connection,limit=50):
    try: rows=connection.execute("SELECT a.message_id,a.event,a.detail,a.created_at,j.company,j.title FROM employer_reply_audit a LEFT JOIN employer_reply_drafts d ON d.message_id=a.message_id LEFT JOIN jobs j ON j.id=d.job_id ORDER BY a.id DESC LIMIT ?",(limit,)).fetchall()
    except Exception: return []
    return [{"message_id":str(r[0]),"event":str(r[1]),"detail":str(r[2]),"created_at":str(r[3]),"company":str(r[4] or ''),"title":str(r[5] or '')} for r in rows]

def build_html(data,due_rows,follow_stats=None,actions=None,pending=None,approved=None,audit=None,delivered=None,archived=None):
    EXPORT_DIR.mkdir(parents=True,exist_ok=True); follow_stats=follow_stats or {}; actions=actions or []; pending=pending or []; approved=approved or []; audit=audit or []; delivered=delivered or []; archived=archived or []
    def attr(item): return escape(' '.join(str(v) for v in item.values()).casefold(),quote=True)
    pending_cards="".join(f"<article class='searchable' data-search='{attr(d)}'><h3>Approval required: {escape(d['company'])}</h3><form method='post' action='/edit'><input type='hidden' name='message_id' value='{escape(d['message_id'],quote=True)}'><label>Subject</label><input name='subject' value='{escape(d['subject'],quote=True)}' required><label>Reply</label><textarea name='body' rows='10' required>{escape(d['body'])}</textarea><button type='submit'>Save changes</button></form><form method='post' action='/approve'><input type='hidden' name='message_id' value='{escape(d['message_id'],quote=True)}'><button type='submit'>Approve reply</button></form></article>" for d in pending)
    approved_cards="".join(f"<article class='searchable' data-search='{attr(d)}'><h3>Approved: {escape(d['company'])}</h3><p><strong>{escape(d['subject'])}</strong></p><pre>{escape(d['body'])}</pre><form method='post' action='/send'><input type='hidden' name='message_id' value='{escape(d['message_id'],quote=True)}'><button type='submit'>Send reply</button></form></article>" for d in approved)
    delivered_rows="".join(f"<tr class='searchable' data-search='{attr(i)}'><td>{escape(i['sent_at'])}</td><td>{escape(i['company'])}</td><td>{escape(i['title'])}</td><td>{escape(i['subject'])}</td><td>{escape(i['delivery_status'])}</td><td><code>{escape(i['gmail_message_id'])}</code></td><td><form method='post' action='/archive'><input type='hidden' name='message_id' value='{escape(i['message_id'],quote=True)}'><button type='submit'>Archive</button></form></td></tr>" for i in delivered)
    archived_rows="".join(f"<tr class='searchable' data-search='{attr(i)}'><td>{escape(i['archived_at'])}</td><td>{escape(i['company'])}</td><td>{escape(i['title'])}</td><td>{escape(i['subject'])}</td><td><code>{escape(i['gmail_message_id'])}</code></td><td><form method='post' action='/restore'><input type='hidden' name='message_id' value='{escape(i['message_id'],quote=True)}'><button type='submit'>Restore</button></form></td></tr>" for i in archived)
    audit_rows="".join(f"<tr class='searchable' data-search='{attr(i)}'><td>{escape(i['created_at'])}</td><td>{escape(i['company'])}</td><td>{escape(i['title'])}</td><td>{escape(i['event'])}</td><td>{escape(i['detail'])}</td></tr>" for i in audit)
    action_cards="".join(f"<article><h3>{escape(i['priority'])}: {escape(i['action'])}</h3><p><strong>{escape(i['company'])}</strong> · {escape(i['title'])}</p><p>{escape(i['classification'])} · {escape(i['subject'])}</p></article>" for i in actions)
    follow_cards="".join(f"<article><h3>{escape(r['title'])}</h3><p><strong>{escape(r['company'])}</strong></p><p>Due: {escape(r['follow_up_date'] or '')}</p></article>" for r in due_rows)
    health="".join(f'<div class="card"><div class="value">{follow_stats.get(k,0)}</div><div>Follow up {label}</div></div>' for k,label in [('pending','pending'),('completed','sent'),('failed','failed'),('cancelled','cancelled')])
    ANALYTICS_FILE.write_text(f"""<!doctype html><html><head><meta charset="utf8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{APP_DISPLAY_NAME} Analytics</title><style>body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;padding:0 18px;background:#f5f7fb;color:#111827}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}}.card,article{{background:white;border:1px solid #dbe1ea;border-radius:12px;padding:18px;margin:10px 0}}.value{{font-size:30px;font-weight:700}}pre{{white-space:pre-wrap;font-family:inherit}}label{{display:block;font-weight:700;margin-top:10px}}input,textarea,select{{width:100%;box-sizing:border-box;padding:10px;margin:6px 0 12px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}}button{{padding:10px 16px;font-weight:700;cursor:pointer;margin-right:8px}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:10px;border:1px solid #dbe1ea;text-align:left;vertical-align:top}}code{{font-size:12px}}.filters{{display:grid;grid-template-columns:2fr 1fr;gap:12px;background:white;padding:14px;border-radius:12px;margin:18px 0}}</style></head><body><h1>{APP_DISPLAY_NAME} Pipeline Analytics</h1><div class="filters"><input id="search" type="search" placeholder="Search company, role, subject, event, Gmail ID"><select id="scope"><option value="all">All reply records</option><option value="pending">Awaiting approval</option><option value="approved">Approved to send</option><option value="delivered">Delivered</option><option value="archived">Archived</option><option value="audit">Audit history</option></select></div><div class="grid"><div class="card"><div class="value">{data['shortlisted']}</div><div>Shortlisted</div></div><div class="card"><div class="value">{data['applied']}</div><div>Applications</div></div><div class="card"><div class="value">{data['interviews']}</div><div>Interviews</div></div><div class="card"><div class="value">{data['offers']}</div><div>Offers</div></div><div class="card"><div class="value">{len(pending)}</div><div>Awaiting approval</div></div><div class="card"><div class="value">{len(approved)}</div><div>Approved to send</div></div><div class="card"><div class="value">{len(delivered)}</div><div>Delivered replies</div></div><div class="card"><div class="value">{len(archived)}</div><div>Archived replies</div></div>{health}</div><section data-scope="pending"><h2>Awaiting approval</h2>{pending_cards or '<p>None.</p>'}</section><section data-scope="approved"><h2>Approved to send</h2>{approved_cards or '<p>None.</p>'}</section><section data-scope="delivered"><h2>Delivered replies</h2><table><thead><tr><th>Sent</th><th>Company</th><th>Role</th><th>Subject</th><th>Status</th><th>Gmail message ID</th><th>Action</th></tr></thead><tbody>{delivered_rows or '<tr><td colspan="7">No delivered replies yet.</td></tr>'}</tbody></table></section><section data-scope="archived"><h2>Archived replies</h2><table><thead><tr><th>Archived</th><th>Company</th><th>Role</th><th>Subject</th><th>Gmail message ID</th><th>Action</th></tr></thead><tbody>{archived_rows or '<tr><td colspan="6">No archived replies.</td></tr>'}</tbody></table></section><section data-scope="audit"><h2>Reply history</h2><table><thead><tr><th>Time</th><th>Company</th><th>Role</th><th>Event</th><th>Detail</th></tr></thead><tbody>{audit_rows or '<tr><td colspan="5">No reply activity yet.</td></tr>'}</tbody></table></section><section><h2>Employer actions</h2>{action_cards or '<p>None.</p>'}</section><section><h2>Follow ups due</h2>{follow_cards or '<p>None.</p>'}</section><script>const q=document.getElementById('search'),s=document.getElementById('scope');function apply(){{const term=q.value.trim().toLowerCase(),scope=s.value;document.querySelectorAll('section[data-scope]').forEach(section=>{{const active=scope==='all'||section.dataset.scope===scope;section.style.display=active?'':'none';section.querySelectorAll('.searchable').forEach(item=>{{item.style.display=!term||item.dataset.search.includes(term)?'':'none'}})}})}}q.addEventListener('input',apply);s.addEventListener('change',apply);</script></body></html>""",encoding='utf8')

def main():
    console=Console(); database=Database()
    try:
        data=database.analytics(SHORTLIST_SCORE); due=database.list_due_follow_ups(); stats=follow_up_statistics(database.connection); actions=response_actions(database.connection); pending=reply_drafts(database.connection,'AWAITING_APPROVAL'); approved=reply_drafts(database.connection,'APPROVED'); audit=reply_audit(database.connection); delivered=delivered_replies(database.connection); archived=delivered_replies(database.connection,archived=True)
        table=Table(title=f"{APP_DISPLAY_NAME} Pipeline Analytics"); table.add_column('Metric'); table.add_column('Value',justify='right')
        for label,value in [('Shortlisted',data['shortlisted']),('Applications',data['applied']),('Interviews',data['interviews']),('Offers',data['offers']),('Awaiting approval',len(pending)),('Approved to send',len(approved)),('Delivered replies',len(delivered)),('Archived replies',len(archived)),('Reply history',len(audit))]: table.add_row(label,str(value))
        console.print(table); build_html(data,due,stats,actions,pending,approved,audit,delivered,archived); return 0
    finally: database.close()

if __name__=='__main__': raise SystemExit(main())
