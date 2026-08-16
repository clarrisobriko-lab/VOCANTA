from __future__ import annotations

import json
import os
from pathlib import Path

SCOPES=["https://www.googleapis.com/auth/gmail.readonly"]


def build_gmail_service(*, token_path: str = "gmail_token.json", credentials_path: str = "gmail_credentials.json"):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials=None
    token=Path(token_path)
    if token.exists(): credentials=Credentials.from_authorized_user_file(str(token),SCOPES)
    elif os.getenv("VOCANTA_GMAIL_TOKEN_JSON","").strip(): credentials=Credentials.from_authorized_user_info(json.loads(os.environ["VOCANTA_GMAIL_TOKEN_JSON"]),SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        source=Path(credentials_path)
        if not source.exists(): raise RuntimeError("Gmail is not configured. Provide gmail_credentials.json or VOCANTA_GMAIL_TOKEN_JSON.")
        flow=InstalledAppFlow.from_client_secrets_file(str(source),SCOPES)
        credentials=flow.run_local_server(port=0)
        token.write_text(credentials.to_json(),encoding="utf8")
    return build("gmail","v1",credentials=credentials,cache_discovery=False)
