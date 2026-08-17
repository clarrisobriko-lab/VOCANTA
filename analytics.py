from html import escape
from rich.console import Console
from rich.table import Table
from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database
from core.follow_up_store import follow_up_statistics
from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response
ANALYTICS_FILE=EXPORT_DIR/"analytics.html"
PAGE_SIZE=10


def _like(query): return f"%{(query or '').strip().casefold()}%"


def query_reply_records(connection,scope='audit',query='',page=1,page_size=PAGE_SIZE):
    page=max(1,int(page)); page_size=max(1,min(100,int(page_size))); offset=(page-1)*page_size; pattern=_like(query)
    if scope in {'pending','approved'}:
        status='AWAITING_APPROVAL' if scope=='pending' else 'APPROVED'
        where="d.status=? AND d.archived_at IS NULL AND (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(d.subject,'')||' '||coalesce(d.body,'')||' '||coalesce(d.message_id,'')) LIKE ?)"
        args=(status,(query or '').strip(),pattern); base="FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE "+where
        select="SELECT d.message_id,d.subject,d.body,d.created_at,j.company,j.title "+base+" ORDER BY d.created_at DESC LIMIT ? OFFSET ?"
        rows=connection.execute(select,args+(page_size,offset)).fetchall(); total=connection.execute("SELECT COUNT(*) "+base,args).fetchone()[0]
        items=[{'message_id':str(r[0]),'subject':str(r[1]),'body':str(r[2]),'created_at':str(r[3]),'company':str(r[4]),'title':str(r[5])} for r in rows]
    elif scope in {'delivered','archived'}:
        archive_clause='IS NOT NULL' if scope=='archived' else 'IS NULL'
        base=f"FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='SENT' AND d.archived_at {archive_clause} AND (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(d.subject,'')||' '||coalesce(d.gmail_sent_message_id,'')||' '||coalesce(d.message_id,'')) LIKE ?)"
        args=((query or '').strip(),pattern); rows=connection.execute("SELECT d.message_id,d.subject,d.sent_at,d.gmail_sent_message_id,d.archived_at,j.company,j.title "+base+" ORDER BY COALESCE(d.archived_at,d.sent_at) DESC LIMIT ? OFFSET ?",args+(page_size,offset)).fetchall(); total=connection.execute("SELECT COUNT(*) "+base,args).fetchone()[0]
        items=[{'message_id':str(r[0]),'subject':str(r[1]),'sent_at':str(r[2] or ''),'gmail_message_id':str(r[3] or ''),'archived_at':str(r[4] or ''),'company':str(r[5]),'title':str(r[6]),'delivery_status':'Gmail accepted' if r[3] else 'Sent'} for r in rows]
    else:
        base="FROM employer_reply_audit a LEFT JOIN employer_reply_drafts d ON d.message_id=a.message_id LEFT JOIN jobs j ON j.id=d.job_id WHERE (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(a.event,'')||' '||coalesce(a.detail,'')||' '||coalesce(a.message_id,'')) LIKE ?)"; args=((query or '').strip(),pattern)
        rows=connection.execute("SELECT a.message_id,a.event,a.detail,a.created_at,j.company,j.title "+base+" ORDER BY a.id DESC LIMIT ? OFFSET ?",args+(page_size,offset)).fetchall(); total=connection.execute("SELECT COUNT(*) "+base,args).fetchone()[0]
        items=[{'message_id':str(r[0]),'event':str(r[1]),'detail':str(r[2]),'created_at':str(r[3]),'company':str(r[4] or ''),'title':str(r[5] or '')} for r in rows]
    pages=max(1,(int(total)+page_size-1)//page_size); return items,{'page':min(page,pages),'pages':pages,'total':int(total),'page_size':page_size}


def response_actions(connection):
    try: rows=connection.execute("SELECT er.classification,er.confidence,er.reason,er.sender,er.subject,er.received_at,j.company,j.title FROM employer_responses er JOIN jobs j ON j.id=er.job_id ORDER BY er.received_at DESC LIMIT 25").fetchall()
    except Exception: return []
    items=[]
    for row in rows:
        response=EmployerResponse(str(row[0]),int(row[1]),str(row[2])); action=action_for_response(response); items.append({'priority':action.priority,'action':action.action,'company':str(row[6]),'title':str(row[7]),'classification':response.status,'subject':str(row[4])})
    order={'URGENT':0,'HIGH':1,'MEDIUM':2,'LOW':3}; return sorted(items,key=lambda item:order.get(item['priority'],9))


def build_query_html(scope,query,items,meta):
    q=escape(query,quote=True); scope=scope if scope in {'pending','approved','delivered','archived','audit'} else 'audit'; rows=[]
    for item in items:
        if scope in {'pending','approved'}: rows.append(f"<tr><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['subject'])}</td><td>{escape(item['created_at'])}</td></tr>")
        elif scope in {'delivered','archived'}: rows.append(f"<tr><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['subject'])}</td><td><code>{escape(item['gmail_message_id'])}</code></td></tr>")
        else: rows.append(f"<tr><td>{escape(item['created_at'])}</td><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['event'])}</td><td>{escape(item['detail'])}</td></tr>")
    headers='<th>Company</th><th>Role</th><th>Subject</th><th>Time</th>' if scope in {'pending','approved'} else ('<th>Company</th><th>Role</th><th>Subject</th><th>Gmail message ID</th>' if scope in {'delivered','archived'} else '<th>Time</th><th>Company</th><th>Role</th><th>Event</th><th>Detail</th>')
    prev=max(1,meta['page']-1); nxt=min(meta['pages'],meta['page']+1)
    return f"""<!doctype html><html><head><meta charset='utf8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{APP_DISPLAY_NAME} Reply Records</title><style>body{{font-family:Arial,sans-serif;max-width:1050px;margin:30px auto;padding:0 18px}}form{{display:flex;gap:10px;margin:20px 0}}input,select,button{{padding:10px;font:inherit}}input{{flex:1}}table{{width:100%;border-collapse:collapse}}th,td{{padding:10px;border:1px solid #ddd;text-align:left}}nav{{display:flex;justify-content:space-between;margin-top:16px}}</style></head><body><h1>Reply records</h1><form method='get'><input name='q' value='{q}' placeholder='Search records'><select name='scope'>{''.join(f"<option value='{s}'{' selected' if s==scope else ''}>{s.title()}</option>" for s in ('pending','approved','delivered','archived','audit'))}</select><button>Search</button></form><p>{meta['total']} records</p><table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows) or '<tr><td>No records found.</td></tr>'}</tbody></table><nav><a href='/?scope={scope}&q={q}&page={prev}'>Previous</a><span>Page {meta['page']} of {meta['pages']}</span><a href='/?scope={scope}&q={q}&page={nxt}'>Next</a></nav></body></html>"""


def main():
    console=Console(); database=Database()
    try:
        data=database.analytics(SHORTLIST_SCORE); table=Table(title=f"{APP_DISPLAY_NAME} Pipeline Analytics"); table.add_column('Metric'); table.add_column('Value',justify='right')
        for label,value in [('Shortlisted',data['shortlisted']),('Applications',data['applied']),('Interviews',data['interviews']),('Offers',data['offers'])]: table.add_row(label,str(value))
        console.print(table); return 0
    finally: database.close()

if __name__=='__main__': raise SystemExit(main())
