from __future__ import annotations

import base64
from email.utils import parseaddr


class GmailInboxSource:
    def __init__(self,service): self.service=service

    def fetch_recent(self,*,query: str="in:inbox newer_than:30d",limit: int=100) -> list[dict]:
        response=self.service.users().messages().list(userId="me",q=query,maxResults=limit).execute(); messages=[]
        for item in response.get("messages",[]):
            raw=self.service.users().messages().get(userId="me",id=item["id"],format="full").execute(); messages.append(self._normalize(raw))
        return messages

    @staticmethod
    def _normalize(raw: dict) -> dict:
        payload=raw.get("payload",{}); headers={h.get("name","").lower():h.get("value","") for h in payload.get("headers",[])}; body=GmailInboxSource._body(payload) or raw.get("snippet","")
        return {"id":raw.get("id",""),"thread_id":raw.get("threadId",""),"internet_message_id":headers.get("message-id",""),"references":headers.get("references",""),"from":parseaddr(headers.get("from",""))[1],"subject":headers.get("subject",""),"body":body,"date":headers.get("date","")}

    @staticmethod
    def _body(part: dict) -> str:
        data=part.get("body",{}).get("data","")
        if data and part.get("mimeType","").startswith("text/plain"):
            try: return base64.urlsafe_b64decode(data+"="*(-len(data)%4)).decode("utf8",errors="ignore")
            except Exception: return ""
        for child in part.get("parts",[]) or []:
            value=GmailInboxSource._body(child)
            if value: return value
        return ""
