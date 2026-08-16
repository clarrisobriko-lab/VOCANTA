from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from analytics import ANALYTICS_FILE, main as rebuild_analytics
from core.database import Database
from core.employer_reply_store import approve_reply_draft


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!='/': self.send_error(404); return
        rebuild_analytics()
        content=Path(ANALYTICS_FILE).read_bytes()
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(content))); self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        if self.path!='/approve': self.send_error(404); return
        length=int(self.headers.get('Content-Length','0')); data=parse_qs(self.rfile.read(length).decode()); message_id=(data.get('message_id') or [''])[0]
        database=Database()
        try: approved=approve_reply_draft(database.connection,message_id)
        finally: database.close()
        self.send_response(303); self.send_header('Location','/'); self.end_headers()
        if not approved: return

    def log_message(self,format,*args): return


def main():
    server=ThreadingHTTPServer(('127.0.0.1',8765),DashboardHandler)
    print('VOCANTA dashboard: http://127.0.0.1:8765')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__=='__main__': raise SystemExit(main())
