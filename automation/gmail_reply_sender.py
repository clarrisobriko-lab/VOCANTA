from __future__ import annotations

import base64
from email.message import EmailMessage


class GmailReplySender:
    def __init__(self,service,from_address: str): self.service=service; self.from_address=from_address

    def send(self,recipient: str,subject: str,body: str,*,thread_id: str="",in_reply_to: str="",references: str="") -> str:
        message=EmailMessage(); message['To']=recipient; message['From']=self.from_address; message['Subject']=subject
        if in_reply_to: message['In-Reply-To']=in_reply_to
        refs=" ".join(v for v in (references,in_reply_to) if v).strip()
        if refs: message['References']=refs
        message.set_content(body)
        raw=base64.urlsafe_b64encode(message.as_bytes()).decode()
        payload={'raw':raw}
        if thread_id: payload['threadId']=thread_id
        response=self.service.users().messages().send(userId='me',body=payload).execute()
        return str(response.get('id',''))
