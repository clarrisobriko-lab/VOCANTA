from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from analytics import ANALYTICS_FILE, main as rebuild_analytics
from automation.employer_reply_delivery import send_approved_reply
from automation.gmail_auth import build_gmail_service
from automation.gmail_reply_sender import GmailReplySender
from automation.profile import load_profile
from core.database import Database
from core.employer_reply_store import approve_reply_draft, update_reply_draft


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!='/': self.send_error(404); return
        rebuild_analytics(); content=Path(ANALYTICS_FILE).read_bytes()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf8'); self.send_header('Content-Length',str(len(content))); self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        if self.path not in {'/edit','/approve','/send'}: self.send_error(404); return
        length=int(self.headers.get('Content-Length','0')); data=parse_qs(self.rfile.read(length).decode()); message_id=(data.get('message_id') or [''])[0]
        database=Database()
        try:
            if self.path=='/edit':
                subject=(data.get('subject') or [''])[0]; body=(data.get('body') or [''])[0]; update_reply_draft(database.connection,message_id,subject,body)
            elif self.path=='/approve': approve_reply_draft(database.connection,message_id)
            else:
                row=database.connection.execute("SELECT status FROM employer_reply_drafts WHERE message_id=?",(message_id,)).fetchone()
                if row is not None and str(row[0])=='APPROVED':
                    profile=load_profile(); service=build_gmail_service(); sender=GmailReplySender(service,profile.email); send_approved_reply(database.connection,message_id,None,sender)
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
