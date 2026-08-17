from html import escape
from rich.console import Console
from rich.table import Table
from config.settings import APP_DISPLAY_NAME, EXPORT_DIR, SHORTLIST_SCORE
from core.database import Database
from core.employer_reply_store import ensure_reply_schema, latest_reply_retention
from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response
ANALYTICS_FILE=EXPORT_DIR/"analytics.html"
PAGE_SIZE=10
RETENTION_TREND_LIMIT=30
RETENTION_ANOMALY_BASELINE_RUNS=20
RETENTION_ANOMALY_MIN_RUNS=5
RETENTION_ANOMALY_SIGMA=3.0

def _like(query): return f"%{(query or '').strip().casefold()}%"
def filter_records(records,query=''):
    term=(query or '').strip().casefold()
    if not term: return list(records)
    return [item for item in records if term in ' '.join(str(value) for value in item.values()).casefold()]
def paginate_records(records,page=1,page_size=PAGE_SIZE):
    records=list(records); page_size=max(1,int(page_size)); pages=max(1,(len(records)+page_size-1)//page_size); page=max(1,min(int(page),pages)); start=(page-1)*page_size
    return records[start:start+page_size],{'page':page,'pages':pages,'total':len(records),'page_size':page_size}
def retention_history(connection,limit=RETENTION_TREND_LIMIT):
    ensure_reply_schema(connection); limit=max(1,min(365,int(limit))); rows=connection.execute("SELECT archived_replies,audit_events,created_at FROM employer_reply_retention_runs ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    return [{'archived_replies':int(r[0]),'audit_events':int(r[1]),'total_removed':int(r[0])+int(r[1]),'created_at':str(r[2])} for r in rows]
def retention_trend(connection,limit=RETENTION_TREND_LIMIT):
    history=retention_history(connection,limit)
    if not history: return {'runs':0,'total_removed':0,'average_removed':0.0,'peak_removed':0,'latest_removed':0,'direction':'flat'}
    totals=[item['total_removed'] for item in history]; recent=totals[:min(5,len(totals))]; previous=totals[min(5,len(totals)):min(10,len(totals))]; recent_average=sum(recent)/len(recent); previous_average=sum(previous)/len(previous) if previous else recent_average
    direction='up' if recent_average>previous_average else ('down' if recent_average<previous_average else 'flat')
    return {'runs':len(history),'total_removed':sum(totals),'average_removed':round(sum(totals)/len(totals),2),'peak_removed':max(totals),'latest_removed':totals[0],'direction':direction}
def retention_anomaly_severity(latest,average,deviation,enough_history=True):
    if not enough_history: return 'warming'
    if latest<=average: return 'normal'
    if deviation<=0: return 'critical' if latest>average else 'normal'
    sigma=(latest-average)/deviation
    if sigma>=6: return 'critical'
    if sigma>=4: return 'high'
    if sigma>=3: return 'elevated'
    return 'normal'
def retention_anomaly_status(connection,limit=RETENTION_ANOMALY_BASELINE_RUNS,min_runs=RETENTION_ANOMALY_MIN_RUNS):
    ensure_reply_schema(connection); rows=connection.execute("SELECT archived_replies+audit_events FROM employer_reply_retention_runs ORDER BY id DESC LIMIT ?",(max(2,int(limit)+1),)).fetchall(); values=[int(row[0]) for row in rows]
    if not values: return {'status':'unavailable','severity':'unavailable','anomalous':False,'latest_removed':0,'baseline_runs':0,'baseline_mean':0.0,'baseline_deviation':0.0,'anomaly_threshold':0.0}
    latest=values[0]; baseline_values=values[1:1+max(1,int(limit))]
    if not baseline_values: return {'status':'warming','severity':'warming','anomalous':False,'latest_removed':latest,'baseline_runs':0,'baseline_mean':0.0,'baseline_deviation':0.0,'anomaly_threshold':0.0}
    average=sum(baseline_values)/len(baseline_values); deviation=(sum((value-average)**2 for value in baseline_values)/len(baseline_values))**0.5 if len(baseline_values)>1 else 0.0; threshold=average+RETENTION_ANOMALY_SIGMA*deviation; enough=len(baseline_values)>=max(2,int(min_runs)); severity=retention_anomaly_severity(latest,average,deviation,enough); anomalous=severity in {'elevated','high','critical'}
    return {'status':'anomaly' if anomalous else ('normal' if enough else 'warming'),'severity':severity,'anomalous':anomalous,'latest_removed':latest,'baseline_runs':len(baseline_values),'baseline_mean':round(average,2),'baseline_deviation':round(deviation,2),'anomaly_threshold':round(threshold,2)}
def reply_drafts(connection,status):
    try: rows=connection.execute("SELECT d.message_id,d.subject,d.body,d.created_at,j.company,j.title FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status=? AND d.archived_at IS NULL ORDER BY d.created_at DESC",(status,)).fetchall()
    except Exception: return []
    return [{'message_id':str(r[0]),'subject':str(r[1]),'body':str(r[2]),'created_at':str(r[3]),'company':str(r[4]),'title':str(r[5])} for r in rows]
def delivered_replies(connection,limit=25,archived=False):
    clause='IS NOT NULL' if archived else 'IS NULL'
    try: rows=connection.execute(f"SELECT d.message_id,d.subject,d.sent_at,d.gmail_sent_message_id,d.archived_at,j.company,j.title FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='SENT' AND d.archived_at {clause} ORDER BY COALESCE(d.archived_at,d.sent_at) DESC LIMIT ?",(limit,)).fetchall()
    except Exception: return []
    return [{'message_id':str(r[0]),'subject':str(r[1]),'sent_at':str(r[2] or ''),'gmail_message_id':str(r[3] or ''),'archived_at':str(r[4] or ''),'company':str(r[5]),'title':str(r[6]),'delivery_status':'Gmail accepted' if r[3] else 'Sent'} for r in rows]
def reply_audit(connection,limit=50):
    try: rows=connection.execute("SELECT a.message_id,a.event,a.detail,a.created_at,j.company,j.title FROM employer_reply_audit a LEFT JOIN employer_reply_drafts d ON d.message_id=a.message_id LEFT JOIN jobs j ON j.id=d.job_id ORDER BY a.id DESC LIMIT ?",(limit,)).fetchall()
    except Exception: return []
    return [{'message_id':str(r[0]),'event':str(r[1]),'detail':str(r[2]),'created_at':str(r[3]),'company':str(r[4] or ''),'title':str(r[5] or '')} for r in rows]
def query_reply_records(connection,scope='audit',query='',page=1,page_size=PAGE_SIZE):
    page=max(1,int(page)); page_size=max(1,min(100,int(page_size))); pattern=_like(query); raw=(query or '').strip()
    if scope in {'pending','approved'}:
        status='AWAITING_APPROVAL' if scope=='pending' else 'APPROVED'; base="FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status=? AND d.archived_at IS NULL AND (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(d.subject,'')||' '||coalesce(d.body,'')||' '||coalesce(d.message_id,'')) LIKE ?)"; args=(status,raw,pattern); columns="d.message_id,d.subject,d.body,d.created_at,j.company,j.title"; order="d.created_at DESC"
    elif scope in {'delivered','archived'}:
        archive_clause='IS NOT NULL' if scope=='archived' else 'IS NULL'; base=f"FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='SENT' AND d.archived_at {archive_clause} AND (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(d.subject,'')||' '||coalesce(d.gmail_sent_message_id,'')||' '||coalesce(d.message_id,'')) LIKE ?)"; args=(raw,pattern); columns="d.message_id,d.subject,d.sent_at,d.gmail_sent_message_id,d.archived_at,j.company,j.title"; order="COALESCE(d.archived_at,d.sent_at) DESC"
    else:
        scope='audit'; base="FROM employer_reply_audit a LEFT JOIN employer_reply_drafts d ON d.message_id=a.message_id LEFT JOIN jobs j ON j.id=d.job_id WHERE (?='' OR lower(coalesce(j.company,'')||' '||coalesce(j.title,'')||' '||coalesce(a.event,'')||' '||coalesce(a.detail,'')||' '||coalesce(a.message_id,'')) LIKE ?)"; args=(raw,pattern); columns="a.message_id,a.event,a.detail,a.created_at,j.company,j.title"; order="a.id DESC"
    total=int(connection.execute("SELECT COUNT(*) "+base,args).fetchone()[0]); pages=max(1,(total+page_size-1)//page_size); page=min(page,pages); offset=(page-1)*page_size; rows=connection.execute(f"SELECT {columns} {base} ORDER BY {order} LIMIT ? OFFSET ?",args+(page_size,offset)).fetchall()
    if scope in {'pending','approved'}: items=[{'message_id':str(r[0]),'subject':str(r[1]),'body':str(r[2]),'created_at':str(r[3]),'company':str(r[4]),'title':str(r[5])} for r in rows]
    elif scope in {'delivered','archived'}: items=[{'message_id':str(r[0]),'subject':str(r[1]),'sent_at':str(r[2] or ''),'gmail_message_id':str(r[3] or ''),'archived_at':str(r[4] or ''),'company':str(r[5]),'title':str(r[6]),'delivery_status':'Gmail accepted' if r[3] else 'Sent'} for r in rows]
    else: items=[{'message_id':str(r[0]),'event':str(r[1]),'detail':str(r[2]),'created_at':str(r[3]),'company':str(r[4] or ''),'title':str(r[5] or '')} for r in rows]
    return items,{'page':page,'pages':pages,'total':total,'page_size':page_size}
def response_actions(connection):
    try: rows=connection.execute("SELECT er.classification,er.confidence,er.reason,er.sender,er.subject,er.received_at,j.company,j.title FROM employer_responses er JOIN jobs j ON j.id=er.job_id ORDER BY er.received_at DESC LIMIT 25").fetchall()
    except Exception: return []
    items=[]
    for row in rows:
        response=EmployerResponse(str(row[0]),int(row[1]),str(row[2])); action=action_for_response(response); items.append({'priority':action.priority,'action':action.action,'company':str(row[6]),'title':str(row[7]),'classification':response.status,'subject':str(row[4])})
    order={'URGENT':0,'HIGH':1,'MEDIUM':2,'LOW':3}; return sorted(items,key=lambda item:order.get(item['priority'],9))
def build_query_html(scope,query,items,meta,retention=None,trend=None,anomaly=None):
    retention=retention or {'archived_replies':0,'audit_events':0,'created_at':''}; trend=trend or {'runs':0,'total_removed':0,'average_removed':0,'peak_removed':0,'latest_removed':0,'direction':'flat'}; anomaly=anomaly or {'status':'unavailable','severity':'unavailable','latest_removed':0,'baseline_runs':0,'baseline_mean':0,'baseline_deviation':0,'anomaly_threshold':0}; q=escape(query,quote=True); scope=scope if scope in {'pending','approved','delivered','archived','audit'} else 'audit'; rows=[]
    for item in items:
        if scope in {'pending','approved'}: rows.append(f"<tr><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['subject'])}</td><td>{escape(item['created_at'])}</td></tr>")
        elif scope in {'delivered','archived'}: rows.append(f"<tr><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['subject'])}</td><td><code>{escape(item['gmail_message_id'])}</code></td></tr>")
        else: rows.append(f"<tr><td>{escape(item['created_at'])}</td><td>{escape(item['company'])}</td><td>{escape(item['title'])}</td><td>{escape(item['event'])}</td><td>{escape(item['detail'])}</td></tr>")
    headers='<th>Company</th><th>Role</th><th>Subject</th><th>Time</th>' if scope in {'pending','approved'} else ('<th>Company</th><th>Role</th><th>Subject</th><th>Gmail message ID</th>' if scope in {'delivered','archived'} else '<th>Time</th><th>Company</th><th>Role</th><th>Event</th><th>Detail</th>'); prev=max(1,meta['page']-1); nxt=min(meta['pages'],meta['page']+1)
    return f"<!doctype html><html><head><meta charset='utf8'><title>{APP_DISPLAY_NAME} Reply Records</title></head><body><h1>Reply records</h1><p>Last retention run: {escape(retention['created_at']) or 'not yet run'}. Removed {retention['archived_replies']} archived replies and {retention['audit_events']} audit events.</p><p>Retention trend across {trend['runs']} runs: {trend['direction']}. Latest {trend['latest_removed']}, average {trend['average_removed']}, peak {trend['peak_removed']}, total {trend['total_removed']} records removed.</p><p>Retention anomaly status: {escape(str(anomaly['status']))}; severity: {escape(str(anomaly['severity']))}. Latest {anomaly['latest_removed']}, baseline mean {anomaly['baseline_mean']}, deviation {anomaly['baseline_deviation']}, anomaly threshold {anomaly['anomaly_threshold']} across {anomaly['baseline_runs']} prior runs.</p><form method='get'><input name='q' value='{q}'><select name='scope'>{''.join(f'<option value={s}>{s.title()}</option>' for s in ('pending','approved','delivered','archived','audit'))}</select><button>Search</button></form><p>{meta['total']} records</p><table><thead><tr>{headers}</tr></thead><tbody>{''.join(rows) or '<tr><td>No records found.</td></tr>'}</tbody></table><nav><a href='/?scope={scope}&q={q}&page={prev}'>Previous</a><span>Page {meta['page']} of {meta['pages']}</span><a href='/?scope={scope}&q={q}&page={nxt}'>Next</a></nav></body></html>"
def main():
    console=Console(); database=Database()
    try:
        data=database.analytics(SHORTLIST_SCORE); retention=latest_reply_retention(database.connection); trend=retention_trend(database.connection); anomaly=retention_anomaly_status(database.connection); table=Table(title=f"{APP_DISPLAY_NAME} Pipeline Analytics"); table.add_column('Metric'); table.add_column('Value',justify='right')
        for label,value in [('Shortlisted',data['shortlisted']),('Applications',data['applied']),('Interviews',data['interviews']),('Offers',data['offers']),('Last retention archives removed',retention['archived_replies']),('Last retention audit events removed',retention['audit_events']),('Retention runs analysed',trend['runs']),('Retention average removed',trend['average_removed']),('Retention peak removed',trend['peak_removed']),('Retention trend',trend['direction']),('Retention anomaly status',anomaly['status']),('Retention anomaly severity',anomaly['severity']),('Retention baseline runs',anomaly['baseline_runs']),('Retention baseline mean',anomaly['baseline_mean']),('Retention anomaly threshold',anomaly['anomaly_threshold'])]: table.add_row(label,str(value))
        console.print(table); return 0
    finally: database.close()
if __name__=='__main__': raise SystemExit(main())
