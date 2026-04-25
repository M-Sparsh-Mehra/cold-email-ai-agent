import os.path
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

# Scope for creating drafts only. Safe!
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

class GmailDraftCreator:
    def __init__(self):
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Handles OAuth2 login and saves the token for future runs."""
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('gmail', 'v1', credentials=self.creds)

    def create_draft(self, to_email, raw_draft_text):
        """Parses the LLM output and creates a Gmail draft."""
        try:
            # Our LLM outputs "SUBJECT: [Subject]\n\n[Body]"
            # Let's split that to format the email properly
            parts = raw_draft_text.split("\n\n", 1)
            subject = parts[0].replace("SUBJECT:", "").strip() if len(parts) > 1 else "Application Inquiry"
            body = parts[1] if len(parts) > 1 else raw_draft_text

            message = EmailMessage()
            message.set_content(body)
            message['To'] = to_email
            message['Subject'] = subject

            # Google requires base64 encoding for the raw message string
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {'message': {'raw': encoded_message}}

            draft = self.service.users().drafts().create(userId="me", body=create_message).execute()
            logging.info(f"📧 Draft created in Gmail! Draft ID: {draft['id']}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create Gmail draft: {e}")
            return False