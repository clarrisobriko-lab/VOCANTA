from __future__ import annotations

import argparse

from automation.employer_reply_delivery import send_approved_reply
from automation.gmail_auth import build_gmail_service
from automation.gmail_reply_sender import GmailReplySender
from automation.profile import load_profile
from core.database import Database
from core.employer_reply_store import approve_reply_draft


def list_pending(connection):
    return connection.execute("SELECT d.message_id,j.company,j.title,d.subject,d.body,d.created_at FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id WHERE d.status='AWAITING_APPROVAL' ORDER BY d.created_at DESC").fetchall()


def show_reply(connection,message_id: str):
    return connection.execute("SELECT d.message_id,j.company,j.title,d.subject,d.body,d.status,r.sender FROM employer_reply_drafts d JOIN jobs j ON j.id=d.job_id LEFT JOIN employer_responses r ON r.message_id=d.message_id WHERE d.message_id=?",(message_id,)).fetchone()


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='reply_operator')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    show=sub.add_parser('show'); show.add_argument('message_id')
    approve=sub.add_parser('approve'); approve.add_argument('message_id')
    send=sub.add_parser('send'); send.add_argument('message_id')
    args=parser.parse_args(argv)
    database=Database()
    try:
        if args.command=='list':
            rows=list_pending(database.connection)
            for row in rows: print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
            return 0
        row=show_reply(database.connection,args.message_id)
        if row is None: print('Reply draft not found'); return 1
        if args.command=='show':
            print(f"Company: {row[1]}\nRole: {row[2]}\nStatus: {row[5]}\nTo: {row[6]}\nSubject: {row[3]}\n\n{row[4]}"); return 0
        if args.command=='approve':
            if approve_reply_draft(database.connection,args.message_id): print('Approved'); return 0
            print('Reply is not awaiting approval'); return 1
        if args.command=='send':
            if str(row[5])!='APPROVED': print('Reply must be approved before sending'); return 1
            profile=load_profile(); service=build_gmail_service(); sender=GmailReplySender(service,profile.email)
            if send_approved_reply(database.connection,args.message_id,None,sender): print('Sent'); return 0
            print('Send failed'); return 1
        return 1
    finally:
        database.close()


if __name__=='__main__': raise SystemExit(main())
