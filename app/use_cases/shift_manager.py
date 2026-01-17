from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from app.infrastructure.storage.sqlite_state import SqliteStateStorage
from app.infrastructure.storage.composite_storage import CompositeHistoryStorage
from app.use_cases.user_manager import UserManager
from app.domain.i_calculator import ICalculator
from app.infrastructure.storage.excel_sites import ExcelSitesRepository
import asyncio
from app.infrastructure.google.drive_manager import GoogleDriveManager

class ShiftController:
    def __init__(self, 
                 state_storage: SqliteStateStorage, 
                 history_storage: CompositeHistoryStorage,
                 calculator: ICalculator,
                 sites_repo: ExcelSitesRepository,
                 user_manager: UserManager,
                 drive_manager: GoogleDriveManager = None):
        self.state_storage = state_storage
        self.history_storage = history_storage
        self.calculator = calculator
        self.sites_repo = sites_repo
        self.user_manager = user_manager
        self.drive_manager = drive_manager

    # --- User Mgmt ---
    def is_user_registered(self, user_id: int) -> bool:
        return self.user_manager.get_user(user_id) is not None

    def register_user(self, user_id: int, username: str, full_name: str, phone: str):
        self.user_manager.register_user(user_id, username, full_name, phone)

    # --- Sites ---
    async def get_available_sites(self) -> List[str]:
        return await self.sites_repo.get_all_sites()

    # --- Shift Flow Step-by-Step ---
    
    def init_shift(self, user_id: int) -> bool:
        """Step 1: User presse Start. Create record."""
        # Check if active exists
        if self.state_storage.get_active_shift(user_id):
            return False
        
        self.state_storage.create_shift(user_id)
        return True

    def set_shift_site(self, user_id: int, site_name: str) -> bool:
        """Step 2: User picked site."""
        shift = self.state_storage.get_active_shift(user_id)
        if not shift: return False
        
        # We could validate site exists here
        self.state_storage.update_shift(shift['shift_id'], {
            "project": site_name,
            "status": "start_site_ok"
        })
        return True

    def set_shift_start_geo(self, user_id: int, geo: str) -> bool:
        """Step 3: User sent Geo."""
        shift = self.state_storage.get_active_shift(user_id)
        if not shift: return False
        
        # Validation Logic Placeholder (Radius check)
        # sites_data = self.sites_repo.get_sites_data()
        # site_info = sites_data.get(shift['project'])
        # if site_info... check dist...
        
        self.state_storage.update_shift(shift['shift_id'], {
            "start_geo": geo,
            "status": "start_geo_ok"
        })
        return True

    async def set_shift_start_video(self, user_id: int, video_id: str, video_link: str = None) -> bool:
        """Step 4: User sent Video. Finalize Start Phase."""
        shift = self.state_storage.get_active_shift(user_id)
        if not shift: return False

        status = "active"
        if "file" in video_id:
             status = "active_warning"

        self.state_storage.update_shift(shift['shift_id'], {
            "start_video_id": video_id,
            "status": status,
            # We can store link in a custom field if DB supports, 
            # or just rely on log. SQLite schema might not have start_video_path column?
            # Creating proper log_data is what matters.
        })
        
        # Log Start Sync (Async Call)
        user = self.user_manager.get_user(user_id)
        user_name = user['full_name'] if user else "Unknown"
        
        # Prepare data for logging
        log_data = {
            "shift_id": shift['shift_id'],
            "user_id": user_id,
            "user_name": user_name,
            "project": shift['project'],
            "start_time": shift['start_time'], # Check format? SQLite returns datetime usually if parsed
            "start_geo": shift.get('start_geo', ''),
            "start_video_path": video_link or "Pending Upload",
            "status": "ACTIVE"
        }
        
        # Fire and forget or await? Await is safer to ensure it's in sheet.
        row_num = await self.history_storage.log_start_shift(log_data)
        
        if row_num:
             self.state_storage.update_shift(shift['shift_id'], {"sheet_row": row_num})

        return True

    # --- End Flow ---
    
    def get_active_shift(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.state_storage.get_active_shift(user_id)

    def set_shift_end_geo(self, user_id: int, geo: str) -> bool:
        shift = self.state_storage.get_active_shift(user_id)
        if not shift: return False
        
        self.state_storage.update_shift(shift['shift_id'], {
            "end_geo": geo,
            "status": "end_geo_ok"
        })
        return True

    async def finalize_shift(self, user_id: int, video_id: str, start_video_link: str = None, end_video_link: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        shift = self.state_storage.get_active_shift(user_id)
        if not shift: return False, "No active shift", {}

        end_time = datetime.now()
        start_time = shift['start_time']
        
        # Calc
        hours = self.calculator.calculate_duration(start_time, end_time)
        
        # Use Drive links if available, otherwise use file_id
        start_video_path = start_video_link if start_video_link else f"tg://{shift.get('start_video_id', 'NO_VIDEO')}"
        end_video_path = end_video_link if end_video_link else f"tg://{video_id}"

        # Check Status
        final_status = shift['status'] # Carry over warnings
        if "|file" in video_id:
             final_status = "completed_warning"
        else:
             if "warning" not in final_status:
                 final_status = "completed_ok"

        # Update DB (Close it)
        self.state_storage.update_shift(shift['shift_id'], {
            "end_time": end_time,
            "end_video_id": video_id,
            "status": final_status,
            "is_active": 0 # Close
        })

        # Log to History (Excel/Google)
        # We need to fetch full Data.
        user = self.user_manager.get_user(user_id)
        user_name = user['full_name'] if user else "Unknown"
        
        log_data = {
            "shift_id": shift['shift_id'],
            "user_id": user_id,
            "user_name": user_name,
            "project": shift['project'],
            "start_time": start_time,
            "end_time": end_time,
            "hours": hours,
            "start_geo": shift['start_geo'],
            "end_geo": geo if 'geo' in locals() else shift.get('end_geo'), # Fixed geo scope issue
            "start_video_path": start_video_path,
            "end_video_path": end_video_path,
            "status": final_status
        }
        
        # Await async logging
        sheet_row = shift.get('sheet_row')
        if sheet_row:
             await self.history_storage.update_shift_end(sheet_row, log_data)
        else:
             await self.history_storage.log_completed_shift(log_data)
        
        return True, "", log_data
    
    async def terminate_shift(self, user_id: int, reason: str) -> bool:
        """Force terminates the shift."""
        shift = self.get_active_shift(user_id)
        if not shift:
             return False
        
        shift_id = shift['shift_id']
        start_time = shift['start_time']
        end_time = datetime.now()
        
        # Calculate hours
        hours_worked = self.calculator.calculate_duration(start_time, end_time)
        
        # Helper to get path
        def get_path(raw):
            if not raw: return "NO_PATH_SAVED"
            parts = raw.split('|')
            if len(parts) >= 3: return parts[2]
            return "NO_PATH_SAVED"

        start_path = get_path(shift.get('start_video_id'))
        
        # Log to Storage
        status = f"TERMINATED: {reason}"
        
        # Get User Name properly
        user = self.user_manager.get_user(user_id)
        user_name = user['full_name'] if user else "Unknown"

        shift_data = {
            "user_id": user_id,
            "user_name": user_name,
            "project": shift['project'],
            "start_time": start_time,
            "end_time": end_time,
            "hours": hours_worked,
            "start_geo": shift['start_geo'],
            "end_geo": "TERMINATED",
            "start_video_path": start_path,
            "end_video_path": "TERMINATED",
            "status": status
        }
        
        # Async Log
        await self.history_storage.log_completed_shift(shift_data)
        
        # Close State
        self.state_storage.update_shift(shift_id, {
            "end_time": end_time,
            "status": status,
            "is_active": 0
        })
        
        return True

    def check_stale_shifts(self, hours: float):
         return self.state_storage.get_all_active_shifts()

    async def handle_manager_message(self, user_id: int, message: str):
        """Emergency reset and manager notification."""
        import uuid
        from datetime import datetime
        
        shift = self.state_storage.get_active_shift(user_id)
        user = self.user_manager.get_user(user_id)
        user_name = user['full_name'] if user else "Unknown"

        if shift:
            # 1. Close Active Shift locally
            shift_id = shift['shift_id']
            end_time = datetime.now()
            
            # Update SQLite
            self.state_storage.update_shift(shift_id, {
                "status": "TERMINATED_BY_MANAGER_MSG",
                "is_active": 0,
                "end_time": end_time
            })
            
            # 2. Update Google Sheet row if exists
            sheet_row = shift.get('sheet_row')
            if sheet_row:
                 # Calculate duration
                 start_time = shift['start_time']
                 duration = end_time - start_time
                 hours_val = round(duration.total_seconds() / 3600, 2)
                 
                 data = {
                     "end_time": end_time,
                     "hours": hours_val,
                     "end_geo": "FORCE_STOP",
                     "end_video_path": "NONE",
                     "status": f"MSG: {message}"
                 }
                 await self.history_storage.update_shift_end(sheet_row, data)
        else:
            # 3. Create a clean message log in Sheets
            from datetime import datetime
            short_id = f"M-{datetime.now().strftime('%H%M%S')}"
            
            log_data = {
                "shift_id": short_id,
                "user_id": user_id,
                "user_name": user_name,
                "project": "MESSAGE_ONLY",
                "start_time": datetime.now(),
                "start_geo": "",
                "start_video_path": "",
                "status": "MESSAGE",
                "comment": message
            }
            await self.history_storage.log_start_shift(log_data)
        
        return True
