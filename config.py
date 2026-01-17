import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "credentials", ".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("WARNING: BOT_TOKEN is not set in .env file")

# List of construction sites for the MVP
SITES = [
    "Object A (Center)",
    "Object B (North)",
    "Object C (South Warehouse)"
]

# Paths for data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

EXCEL_FILE = os.getenv("EXCEL_FILE", os.path.join(DATA_DIR, "shifts_log.xlsx"))
DB_FILE = os.getenv("DB_FILE", os.path.join(DATA_DIR, "bot_database.db"))

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1fgE-zc0d2IPWSyKx6HN0QNlyH3upca7Y")
