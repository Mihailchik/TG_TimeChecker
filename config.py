import os
from dotenv import load_dotenv

# Load .env from credentials folder
load_dotenv(os.path.join(os.path.dirname(__file__), "credentials", ".env"))

# --- Required Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Validation ---
missing_vars = []
if not BOT_TOKEN: 
    missing_vars.append("BOT_TOKEN")

if missing_vars:
    print("\n" + "!"*60)
    print("❌ CRITICAL ERROR: Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nPlease configure the credentials/.env file.")
    print("Setup instructions: docs/SETUP.md")
    print("!"*60 + "\n")

# --- Optional Integrations ---
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "")

if not GOOGLE_SHEET_ID:
    print("⚠️ WARNING: GOOGLE_SHEET_ID is not set. Google Sheets integration disabled.")
if not DRIVE_FOLDER_ID:
    print("⚠️ WARNING: DRIVE_FOLDER_ID is not set. Google Drive video upload disabled.")

# --- Site Settings ---
SITES = [
    "Object A (Center)",
    "Object B (North)",
    "Object C (South Warehouse)"
]

# --- Paths for Data Files ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

EXCEL_FILE = os.getenv("EXCEL_FILE", os.path.join(DATA_DIR, "shifts_log.xlsx"))
DB_FILE = os.getenv("DB_FILE", os.path.join(DATA_DIR, "bot_database.db"))
