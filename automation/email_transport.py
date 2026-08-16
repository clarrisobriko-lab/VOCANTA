from __future__ import annotations

from email.message import EmailMessage
import smtplib

from intelligence.follow_up_messages import FollowUpMessage


class SMTPFollowUpSender:
    """Standards based email transport. Credentials stay in runtime configuration, never source control."""

    def __init__(self, host: str, port: int, username: str, password: str, from_address: str | None = None, *, use_tls: bool = True, timeout: int = 30):
        self.host=host; self.port=port; self.username=username; self.password=password
        self.from_address=from_address or username; self.use_tls=use_tls; self.timeout=timeout

    def send(self, recipient: str, message: FollowUpMessage) -> str:
        mail=EmailMessage(); mail['From']=self.from_address; mail['To']=recipient; mail['Subject']=message.subject; mail.set_content(message.body)
        with smtplib.SMTP(self.host,self.port,timeout=self.timeout) as client:
            client.ehlo()
            if self.use_tls:
                client.starttls(); client.ehlo()
            if self.username:
                client.login(self.username,self.password)
            client.send_message(mail)
        return mail['Message ID'] if mail['Message ID'] else f"smtp:{recipient}:{message.subject}"


class SMTPAlertSender:
    def __init__(self, host: str, port: int, username: str, password: str, recipient: str, from_address: str | None = None, *, use_tls: bool = True, timeout: int = 30):
        self.host=host; self.port=port; self.username=username; self.password=password; self.recipient=recipient
        self.from_address=from_address or username; self.use_tls=use_tls; self.timeout=timeout

    def send(self, subject: str, body: str) -> str:
        mail=EmailMessage(); mail['From']=self.from_address; mail['To']=self.recipient; mail['Subject']=subject; mail.set_content(body)
        with smtplib.SMTP(self.host,self.port,timeout=self.timeout) as client:
            client.ehlo()
            if self.use_tls:
                client.starttls(); client.ehlo()
            if self.username:
                client.login(self.username,self.password)
            client.send_message(mail)
        return mail['Message ID'] if mail['Message ID'] else f"smtp:{self.recipient}:{subject}"
