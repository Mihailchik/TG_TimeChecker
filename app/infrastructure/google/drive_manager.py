from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from typing import Optional
import os

class GoogleDriveManager:
    """Менеджер для работы с Google Drive"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, credentials_path: str = None, oauth_creds=None):
        self.credentials_path = credentials_path
        self.oauth_creds = oauth_creds
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        try:
            if self.oauth_creds:
                self.service = build('drive', 'v3', credentials=self.oauth_creds)
                return
            
            if not self.credentials_path:
                raise ValueError("Credentials missing")
            
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            print(f"Drive Auth Error: {e}")
    
    def upload_file(self, local_file_path: str, parent_folder_id: Optional[str] = None, new_name: Optional[str] = None) -> Optional[str]:
        try:
            if not os.path.exists(local_file_path):
                return None
            
            file_name = new_name if new_name else os.path.basename(local_file_path)
            file_metadata = {'name': file_name}
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            media = MediaFileUpload(local_file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            return file.get('webViewLink') # Return Link directly for usage
            
        except Exception as e:
            print(f"Upload Error: {e}")
            return None

    def ensure_folder(self, folder_name: str, parent_id: str = None) -> Optional[str]:
        """Finds or creates a folder."""
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(q=query, fields="files(id)").execute()
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            # Create
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                metadata['parents'] = [parent_id]
                
            folder = self.service.files().create(body=metadata, fields='id').execute()
            return folder.get('id')
        except Exception as e:
            print(f"Folder Error: {e}")
            return None
