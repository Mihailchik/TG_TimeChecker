from typing import Dict, Any, List, Optional
import asyncio
from app.domain.i_storage import IHistoryStorage
from app.infrastructure.google.sheets_manager import GoogleSheetsManager

class GoogleSheetsStorage(IHistoryStorage):
    def __init__(self, credentials_file: str = None, spreadsheet_title: str = "TG_Logs", oauth_creds = None):
        self.manager = GoogleSheetsManager(credentials_path=credentials_file, oauth_creds=oauth_creds)
        self.spreadsheet_id = None
        
        # 15 Columns structure
        self.columns = [
            "Event ID", "User ID", "Worker", "Project", 
            "Start Date", "Start Time", "End Date", "End Time", 
            "Work Hours (hrs)", "Start Geo", "End Geo", 
            "Start Video", "End Video", "Status", "Comment"
        ]

    def set_spreadsheet_id(self, sid: str):
        self.spreadsheet_id = sid
        # Force update headers
        self.manager.update_data(sid, "Shifts!A1:O1", [self.columns])

    async def log_completed_shift(self, shift_data: Dict[str, Any]) -> bool:
        if not self.spreadsheet_id: return False
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._log_sync, shift_data)

    def _log_sync(self, shift_data: Dict[str, Any]) -> bool:
        try:
            row = self._build_row(shift_data, "OK")
            self.manager.append_data(self.spreadsheet_id, "Shifts!A1", [row])
            return True
        except Exception as e:
            print(f"Sheet Log Error: {e}")
            return False

    async def log_start_shift(self, shift_data: Dict[str, Any]) -> Optional[int]:
        if not self.spreadsheet_id: return None
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._log_start_sync, shift_data)

    def _log_start_sync(self, shift_data: Dict[str, Any]) -> Optional[int]:
        try:
            row = self._build_row(shift_data, "ACTIVE")
            result = self.manager.append_data(self.spreadsheet_id, "Shifts!A1", [row])
            
            if result and 'updates' in result and 'updatedRange' in result['updates']:
                range_str = result['updates']['updatedRange']
                try:
                    cell_range = range_str.split('!')[-1]
                    start_cell = cell_range.split(':')[0]
                    row_num = int("".join(filter(str.isdigit, start_cell)))
                    
                    # Style: Light Blue for Active
                    self.manager.format_row(self.spreadsheet_id, "Shifts", row_num, {"red": 0.85, "green": 0.9, "blue": 1.0})
                    
                    return row_num
                except: pass
            return None
        except Exception as e:
            print(f"Log Start Error: {e}")
            return None

    async def update_shift_end(self, row_num: int, shift_data: Dict[str, Any]) -> bool:
        if not self.spreadsheet_id or not row_num: return False
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._update_end_sync, row_num, shift_data)

    def _update_end_sync(self, row_num: int, shift_data: Dict[str, Any]) -> bool:
        try:
            end_time = shift_data.get('end_time') or shift_data.get('start_time')
            end_date_str = end_time.strftime("%Y-%m-%d")
            end_time_str = end_time.strftime("%H:%M:%S")
            hours = shift_data.get('hours', 0)
            status = shift_data.get('status', 'OK')
            
            # G, H, I (End Date, End Time, Hours)
            self.manager.update_data(self.spreadsheet_id, f"Shifts!G{row_num}:I{row_num}", 
                                    [[end_date_str, end_time_str, hours]])
            
            # K (End Geo)
            self.manager.update_data(self.spreadsheet_id, f"Shifts!K{row_num}", [[shift_data.get('end_geo', '')]])
            
            # M, N (End Video, Status)
            self.manager.update_data(self.spreadsheet_id, f"Shifts!M{row_num}:N{row_num}", 
                                    [[shift_data.get('end_video_path', ''), status]])
            
            # STYLING
            color = {"red": 0.85, "green": 0.95, "blue": 0.85} # OK (Green)
            if "MSG" in status or "MESSAGE" in status:
                color = {"red": 1.0, "green": 1.0, "blue": 0.85} # Message (Yellow)
            elif "ERROR" in status or "TERMINATED" in status:
                color = {"red": 1.0, "green": 0.85, "blue": 0.85} # Error (Red)
                
            self.manager.format_row(self.spreadsheet_id, "Shifts", row_num, color)
            
            return True
        except Exception as e:
            print(f"Update End Error: {e}")
            return False

    def _build_row(self, data: Dict[str, Any], status: str) -> List[Any]:
        start_time = data.get('start_time')
        start_date = start_time.strftime("%Y-%m-%d") if start_time else ""
        start_clock = start_time.strftime("%H:%M:%S") if start_time else ""
        
        end_time = data.get('end_time')
        end_date = end_time.strftime("%Y-%m-%d") if end_time else ""
        end_clock = end_time.strftime("%H:%M:%S") if end_time else ""
        
        return [
            str(data.get('shift_id', '')),     # A: Event ID
            str(data.get('user_id', '')),      # B: User ID
            data.get('user_name', ''),         # C: Worker
            data.get('project', ''),           # D: Project
            start_date,                        # E: Start Date
            start_clock,                       # F: Start Time
            end_date,                          # G: End Date
            end_clock,                         # H: End Time
            data.get('hours', ""),             # I: Work Hours
            data.get('start_geo', ''),         # J: Start Geo
            data.get('end_geo', ''),           # K: End Geo
            data.get('start_video_path', ''),  # L: Start Video
            data.get('end_video_path', ''),    # M: End Video
            status if status != "OK" else data.get('status', 'OK'), # N: Status
            data.get('comment', '')            # O: Comment
        ]
