import os
import pandas as pd
from typing import Dict, Any
from app.domain.i_storage import IHistoryStorage
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ExcelHistoryStorage(IHistoryStorage):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1) # Serial writes
        # Use columns defined before
        self.columns = [
            "Event ID", "User ID", "Worker", "Project", "Date", 
            "Start Time", "End Time", "Work Hours (hrs)", 
            "Start Geo", "End Geo", "Start Video", "End Video", "Status"
        ]
        self._init_file()

    def _init_file(self):
        if not os.path.exists(self.filepath):
            with pd.ExcelWriter(self.filepath, engine='openpyxl') as writer:
                pd.DataFrame(columns=self.columns).to_excel(writer, sheet_name="Shifts", index=False)
                pd.DataFrame(columns=["User ID", "Username", "Full Name", "Phone", "Registered At"]).to_excel(writer, sheet_name="Users", index=False)
                pd.DataFrame({"Site Name": ["Объект 1"], "Lat": [0.0], "Lon": [0.0], "Radius": [500]}).to_excel(writer, sheet_name="Sites", index=False)

    async def log_completed_shift(self, shift_data: Dict[str, Any]) -> bool:
        async with self.lock:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self.executor, self._write_sync, shift_data)

    def _write_sync(self, shift_data: Dict[str, Any]) -> bool:
        try:
            start_time = shift_data['start_time']
            end_time = shift_data['end_time']
            
            date_str = start_time.strftime("%Y-%m-%d")
            start_str = start_time.strftime("%H:%M:%S")
            end_str = end_time.strftime("%H:%M:%S")
            status = shift_data.get('status', 'OK')

            new_record = {
                "Event ID": shift_data.get('shift_id'),
                "User ID": shift_data.get('user_id'),
                "Worker": shift_data['user_name'],
                "Project": shift_data['project'],
                "Date": date_str,
                "Start Time": start_str,
                "End Time": end_str,
                "Work Hours (hrs)": shift_data['hours'],
                "Start Geo": shift_data.get('start_geo'),
                "End Geo": shift_data.get('end_geo'),
                "Start Video": shift_data.get('start_video_path'),
                "End Video": shift_data.get('end_video_path'),
                "Status": status
            }

            df = pd.read_excel(self.filepath, sheet_name="Shifts")
            new_row_df = pd.DataFrame([new_record])
            df = pd.concat([df, new_row_df], ignore_index=True)
            
            with pd.ExcelWriter(self.filepath, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name="Shifts", index=False)
            return True
        except Exception as e:
            print(f"Excel Async Write Error: {e}")
            return False
