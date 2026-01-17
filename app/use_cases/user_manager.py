import sqlite3
from typing import Optional, Dict, Any
import pandas as pd
import os

class UserManager:
    def __init__(self, db_file: str, excel_file: str = None, google_storage = None):
        self.db_file = db_file
        self.excel_file = excel_file
        self.google_storage = google_storage
        self._init_db()

    def set_google_storage(self, storage):
        self.google_storage = storage

    def _init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    phone_number TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def register_user(self, user_id: int, username: str, full_name: str, phone: str):
        # 1. SQLite
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, full_name, phone_number)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, phone))
            conn.commit()
            
        # 2. Excel Sync
        if self.excel_file and os.path.exists(self.excel_file):
            try:
                # Add to Users sheet
                new_user = {
                    "User ID": user_id,
                    "Username": username,
                    "Full Name": full_name,
                    "Phone": phone,
                    "Registered At": pd.Timestamp.now()
                }
                
                try:
                    df = pd.read_excel(self.excel_file, sheet_name="Users")
                    df = df[df["User ID"] != user_id]
                    
                    new_row = pd.DataFrame([new_user])
                    df = pd.concat([df, new_row], ignore_index=True)
                    
                    with pd.ExcelWriter(self.excel_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                        df.to_excel(writer, sheet_name="Users", index=False)
                except ValueError:
                    pass
            except Exception as e:
                print(f"User Excel Sync Error: {e}")

        # 3. Google Sync
        if self.google_storage:
             try:
                 import datetime
                 now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                 # Order: User ID, Username, Full Name, Phone, Reg Date
                 row = [str(user_id), username or "", full_name, phone, now]
                 
                 # First ensure headers
                 headers = ["User ID", "Username", "Full Name", "Phone", "Registration Date"]
                 self.google_storage.manager.ensure_sheet_headers(
                     self.google_storage.spreadsheet_id, 
                     "Users", 
                     headers
                 )
                 
                 print(f"📝 Syncing User {user_id} to Google Sheets...")
                 self.google_storage.manager.append_data(
                     self.google_storage.spreadsheet_id, 
                     "Users!A1", 
                     [row]
                 )
             except Exception as e:
                 print(f"❌ Google User Sync Error: {e}")

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "full_name": row[2],
                    "phone": row[3]
                }
        return None
