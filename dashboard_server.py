from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from analytics import PAGE_SIZE, build_query_html, query_reply_records
from automation.employer_reply_delivery import send_approved_reply
from automation.gmail_auth import build_gmail_service
from automation.gmail_reply_sender import GmailReplySender
from automation.profile import load_profile
from core.database import Database
from core.employer_reply_store import approve_reply_draft, archive_reply, restore_reply, update_reply_draft


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path!='/': self.send_error(404); return
        params=parse_qs(parsed.query); scope=(params.get('scope') or ['audit'])[0]; query=(params.get('q') or [''])[0]
        try: page=max(1,int((params.get('page') or ['1'])[0]))
        except ValueError: page=1
        database=Database()
        try: items,meta=query_reply_records(database.connection,scope,query,page,PAGE_SIZE); content=build_query_html(scope,query,items,meta).encode()
        finally: database.close()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf8'); self.send_header('Content-Length',str(len(content))); self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        parsed=urlparse(self.path)
        if parsed.path not in {'/edit','/approve','/send','/archive','/restore'}: self.send_error(404); return
        length=int(self.headers.get('Content-Length','0')); data=parse_qs(self.rfile.read(length).decode()); message_id=(data.get('message_id') or [''])[0]
        database=Database()
        try:
            if parsed.path=='/edit': update_reply_draft(database.connection,message_id,(data.get('subject') or [''])[0],(data.get('body') or [''])[0])
            elif parsed.path=='/approve': approve_reply_draft(database.connection,message_id)
            elif parsed.path=='/archive': archive_reply(database.connection,message_id)
            elif parsed.path=='/restore': restore_reply(database.connection,message_id)
            else:
                row=database.connection.execute("SELECT status,archived_at FROM employer_reply_drafts WHERE message_id=?",(message_id,)).fetchone()
                if row is not None and str(row[0])=='APPROVED' and row[1] is None:
                    profile=load_profile(); sender=GmailReplySender(build_gmail_service(),profile.email); send_approved_reply(database.connection,message_id,None,sender)
        finally: database.close()
        self.send_response(303); self.send_header('Location','/'); self.end_headers()

    def log_message(self,format,*args): return


def main():
    server=ThreadingHTTPServer(('127.0.0.1',8765),DashboardHandler); print('VOCANTA dashboard ready on local port 8765')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__=='__main__': raise SystemExit(main())
