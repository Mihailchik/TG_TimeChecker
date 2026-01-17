import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GoogleOAuthManager:
    """Менеджер OAuth 2.0 аутентификации"""
    
    # Scopes для полного доступа
    SCOPES = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/documents'
    ]
    
    def __init__(self, oauth_credentials_path: str, token_path: str):
        self.oauth_credentials_path = oauth_credentials_path
        self.token_path = token_path
        self.creds = None
    
    def authenticate(self) -> Credentials:
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.oauth_credentials_path):
                    raise FileNotFoundError(f"OAuth credentials not found: {self.oauth_credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_credentials_path,
                    self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        return self.creds
