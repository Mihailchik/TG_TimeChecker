import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.domain.i_storage import IStateStorage

class SqliteStateStorage(IStateStorage):
    def __init__(self, db_file: str):
        self.db_file = db_file
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_shifts (
                    shift_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    start_time TIMESTAMP,
                    project TEXT,
                    start_geo TEXT,
                    start_video_id TEXT,
                    status TEXT,
                    start_video_path TEXT,
                    sheet_row INTEGER,
                    end_time TIMESTAMP,
                    end_geo TEXT,
                    end_video_id TEXT,
                    comment TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()

    def create_shift(self, user_id: int) -> str:
        """Creates a new shift record and returns its sequential ID."""
        start_time = datetime.now()
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            # Find next sequential ID
            # Better: use MAX(CAST(shift_id as INTEGER)) if they are numeric
            try:
                cursor.execute("SELECT COUNT(*) FROM active_shifts")
                count = cursor.fetchone()[0]
                new_id = str(count + 1)
            except:
                new_id = "1"

            cursor.execute("""
                INSERT INTO active_shifts (shift_id, user_id, status, start_time, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (new_id, user_id, 'init', start_time))
            conn.commit()
            return new_id

    def update_shift(self, shift_id: str, data: Dict[str, Any]):
        """Updates fields dynamically."""
        if not data: return
        set_clause = []
        values = []
        for key, value in data.items():
            set_clause.append(f"{key} = ?")
            values.append(value)
        values.append(shift_id)
        
        sql = f"UPDATE active_shifts SET {', '.join(set_clause)} WHERE shift_id = ?"
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, values)
            conn.commit()

    def get_active_shift(self, user_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM active_shifts WHERE user_id = ? AND is_active = 1", (user_id,))
            row = cursor.fetchone()
            
        if row:
            d = dict(row)
            # Parse datetime
            if isinstance(d['start_time'], str):
                try: d['start_time'] = datetime.fromisoformat(d['start_time'])
                except: pass
            return d
        return None

    def get_all_active_shifts(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM active_shifts WHERE is_active = 1")
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
             d = dict(row)
             if isinstance(d['start_time'], str):
                try: d['start_time'] = datetime.fromisoformat(d['start_time'])
                except: pass
             results.append(d)
        return results

    def remove_active_shift(self, user_id: int) -> bool:
         with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE active_shifts SET is_active = 0 WHERE user_id = ? AND is_active = 1", (user_id,))
            conn.commit()
         return True
