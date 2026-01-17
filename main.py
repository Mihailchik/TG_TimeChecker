import asyncio
import logging
import sys
import fcntl
import os

# Force Single Instance
try:
    lock_file = open("bot.lock", "w")
    fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
    print("❌ ANOTHER INSTANCE IS RUNNING! STOPPING.")
    sys.exit(1)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, DB_FILE, EXCEL_FILE, GOOGLE_SHEET_ID
from app.infrastructure.storage.sqlite_state import SqliteStateStorage
from app.infrastructure.storage.excel_storage import ExcelHistoryStorage
from app.domain.calculator import StandardTimeCalculator
from app.use_cases.shift_manager import ShiftController
from app.presentation.telegram.router_aggregator import setup_router

from app.infrastructure.storage.excel_sites import ExcelSitesRepository
from app.infrastructure.storage.composite_storage import CompositeHistoryStorage
from app.infrastructure.google.drive_manager import GoogleDriveManager
from app.infrastructure.google.sheets_manager import GoogleSheetsManager
from app.infrastructure.storage.google_sheets_storage import GoogleSheetsStorage
from app.use_cases.user_manager import UserManager
from app.use_cases.video.video_upload import VideoUploadService

async def stale_shift_checker(bot: Bot, controller: ShiftController):
    """Background task to check for long shifts."""
    while True:
        try:
            # Check every hour
            await asyncio.sleep(3600) 
            
            # Get shifts active for > 24 hours
            stale_shifts = controller.check_stale_shifts(hours_threshold=24.0)
            
            for shift in stale_shifts:
                user_id = shift['user_id']
                # Notification
                try:
                    await bot.send_message(
                        user_id,
                        "⚠️ <b>Внимание!</b>\n"
                        "Ваша смена длится более 24 часов.\n"
                        "Пожалуйста, не забудьте завершить работу, если вы уже закончили."
                    )
                except Exception as e:
                    logging.error(f"Failed to send alert to {user_id}: {e}")
                    
        except Exception as e:
            logging.error(f"Background Check Error: {e}")
            await asyncio.sleep(60) # prevent loop spam on error

async def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing in .env")
        return

    # 1. Initialize Infrastructure
    state_storage = SqliteStateStorage(DB_FILE)
    
    # Init UserManager early to allow Google injection
    user_manager = UserManager(DB_FILE, EXCEL_FILE)
    
    # History Storages (Google first, Excel as backup)
    storages = []
    
    # Google Services (OAuth 2.0)
    oauth_creds_path = os.path.join("credentials", "client_secret.json")
    token_pickle = os.path.join("credentials", "token.pickle")
    drive_manager = None
    video_service = None
    google_storage = None
    
    if os.path.exists(oauth_creds_path):
        try:
             print("🔑 Init Google OAuth 2.0...")
             from app.infrastructure.google.auth_manager import GoogleOAuthManager
             
             auth_mgr = GoogleOAuthManager(oauth_creds_path, token_pickle)
             creds = auth_mgr.authenticate() # Opens browser if needed
             
             # Init Drive
             drive_manager = GoogleDriveManager(oauth_creds=creds)
             print("✅ Google Drive Manager Enabled (User Auth)")
             
             # Init Video Service
             from config import DRIVE_FOLDER_ID
             video_service = VideoUploadService(drive_manager, DRIVE_FOLDER_ID)
             print(f"✅ Video Upload Service (Folder: {DRIVE_FOLDER_ID})")
             
             # Init Sheets
             if GOOGLE_SHEET_ID:
                 google_storage = GoogleSheetsStorage(oauth_creds=creds)
                 google_storage.set_spreadsheet_id(GOOGLE_SHEET_ID)
                 storages.append(google_storage)
                 user_manager.set_google_storage(google_storage)
                 print(f"✅ Google Sheets - PRIMARY STORAGE (ID: {GOOGLE_SHEET_ID})")
             else:
                 print("⚠️ GOOGLE_SHEET_ID missing.")
                 
        except Exception as e:
            print(f"❌ OAuth Init Failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"⚠️ {oauth_creds_path} not found. Google Services disabled.")
    
    # Excel (Backup)
    excel_storage = ExcelHistoryStorage(EXCEL_FILE)
    storages.append(excel_storage)
    print("✅ Excel - BACKUP STORAGE")

    history_storage = CompositeHistoryStorage(storages)
    
    if google_storage and GOOGLE_SHEET_ID:
        from app.infrastructure.storage.google_sites_repo import GoogleSitesRepository
        print("✅ Using Google Sites Repository (Synced with Sheets)")
        sites_repo = GoogleSitesRepository(google_storage.manager, GOOGLE_SHEET_ID)
    else:
        print("⚠️ Using Excel Sites Repository (Local only)")
        sites_repo = ExcelSitesRepository(EXCEL_FILE)
    calculator = StandardTimeCalculator()

    # 2. Initialize Logic
    # Pass drive_manager
    controller = ShiftController(state_storage, history_storage, calculator, sites_repo, user_manager, drive_manager)

    # 3. Initialize UI
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Setup Router
    router = setup_router(controller, video_service)
    dp.include_router(router)

    # 4. Start Background Tasks
    asyncio.create_task(stale_shift_checker(bot, controller))

    # Start
    print("Modular Bot Started with Background Service!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
