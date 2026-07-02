import os
import json
import time
from typing import Optional, Dict
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class OAuth2Manager:
    def __init__(self, client_id: str, client_secret: str, token_dir: str,
                 account_name: str = "default"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_dir = Path(token_dir).expanduser()
        self.token_dir.mkdir(parents=True, exist_ok=True)
        self.account_name = account_name
        self.token_file = self.token_dir / f"token_{account_name}.json"
        self.creds: Optional[Credentials] = None
        self._load_credentials()

    def _load_credentials(self):
        if self.token_file.exists():
            try:
                self.creds = Credentials.from_authorized_user_file(
                    str(self.token_file), SCOPES
                )
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")
                self.creds = None

    def get_credentials(self) -> Credentials:
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    self._save_credentials()
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    self.creds = None
                    self._authorize()
            else:
                self._authorize()
        return self.creds

    def _authorize(self):
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8080/"],
                }
            },
            SCOPES,
        )
        self.creds = flow.run_local_server(port=8080, open_browser=True)
        self._save_credentials()

    def _save_credentials(self):
        if self.creds:
            with open(self.token_file, "w") as f:
                f.write(self.creds.to_json())
            logger.info(f"Credentials saved to {self.token_file}")