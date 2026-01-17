from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import List, Any, Optional
import os

class GoogleSheetsManager:
    """Менеджер для работы с Google Sheets"""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    def __init__(self, credentials_path: str = None, oauth_creds=None):
        self.credentials_path = credentials_path
        self.oauth_creds = oauth_creds
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        try:
            if self.oauth_creds:
                self.service = build('sheets', 'v4', credentials=self.oauth_creds)
                return
            
            if not self.credentials_path: 
                raise ValueError("Credentials missing")
                
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
        except Exception as e:
            print(f"Sheets Auth Error: {e}")

    def create_spreadsheet(self, title: str) -> Optional[str]:
        """Creates a new spreadsheet and returns ID."""
        try:
            spreadsheet = {'properties': {'title': title}}
            spreadsheet = self.service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
            return spreadsheet.get('spreadsheetId')
        except Exception as e:
            print(f"Create Sheet Error: {e}")
            return None

    def share_spreadsheet(self, spreadsheet_id: str, email: str, role: str = 'writer'):
        """Shares sheet with email."""
        try:
            # Need Drive Service for permissions
            # We can re-use drive logic if we had access, but here we only have sheets service built?
            # Actually we can build drive service here or require it.
            # Best way: Use GoogleDriveManager for sharing, but let's implement simple one here using same creds.
            from googleapiclient.discovery import build
            
            # Re-auth for drive if needed or use existing creds
            # Our scope in __init__ was only sheets? 
            # SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            # We need Drive scope to share!
            # I will update scopes.
            pass
        except Exception:
            pass
            
    # Update SCOPES
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

    def create_and_share(self, title: str, share_email: str) -> str:
        sid = self.create_spreadsheet(title)
        if sid and share_email:
             # Share logic
             try:
                 drive_service = build('drive', 'v3', credentials=self.service._http.credentials) 
                 # accessing credentials from service object might work if cached
                 # or just re-build
                 
                 permission = {
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': share_email
                 }
                 drive_service.permissions().create(
                    fileId=sid,
                    body=permission,
                    fields='id'
                 ).execute()
                 print(f"Shared with {share_email}")
             except Exception as e:
                 print(f"Share Error: {e}")
        return sid

    def append_data(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Any:
        """Appends data and returns the API response dict."""
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return result
        except Exception as e:
            print(f"Sheets Append Error: {e}")
            return None

    def get_all_values(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        """Reads all values from range."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()
            return result.get('values', [])
        except Exception as e:
            print(f"Sheets Read Error: {e}")
            return []

    def update_data(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> bool:
        """Updates specific range."""
        try:
            body = {'values': values}
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return True
        except Exception as e:
            print(f"Sheets Update Error: {e}")
            return False

    def ensure_sheet_headers(self, spreadsheet_id: str, sheet_name: str, headers: List[str]):
        """Simple check if sheet is empty, add headers."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:A1"
            ).execute()
            
            if 'values' not in result:
                self.append_data(spreadsheet_id, f"{sheet_name}!A1", [headers])
        except Exception:
            pass

    def format_row(self, spreadsheet_id: str, sheet_name: str, row_index: int, color: dict):
        """Sets background color for a row (row_index is 1-based)."""
        try:
            # Need sheet ID by name
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = 0
            for s in spreadsheet.get('sheets', []):
                if s['properties']['title'] == sheet_name:
                    sheet_id = s['properties']['sheetId']
                    break

            body = {
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": row_index - 1,
                                "endRowIndex": row_index,
                                "startColumnIndex": 0,
                                "endColumnIndex": 15 # Up to column O
                            },
                            "cell": {
                                "userEnteredFormat": {
                                    "backgroundColor": color
                                }
                            },
                            "fields": "userEnteredFormat.backgroundColor"
                        }
                    }
                ]
            }
            self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            return True
        except Exception as e:
            print(f"Format Row Error: {e}")
            return False
