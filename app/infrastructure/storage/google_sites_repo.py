from typing import List, Dict, Tuple
from app.infrastructure.google.sheets_manager import GoogleSheetsManager
import asyncio

class GoogleSitesRepository:
    def __init__(self, manager: GoogleSheetsManager, spreadsheet_id: str):
        self.manager = manager
        self.spreadsheet_id = spreadsheet_id
        # Cache sites to avoid hitting Google API every click
        self._cache = []
        self._last_update = 0
        self._update_interval = 60 # Check every minute? Or just on demand?

    async def get_all_sites(self) -> List[str]:
        # Async wrapper for sync google call
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_sites_sync)

    def _get_sites_sync(self) -> List[str]:
        # Format in Sheet "Sites": [Site Name, Lat, Lon, Radius] (from fix_google_sheet.py)
        # We need Site Name (Column A)
        
        rows = self.manager.get_all_values(self.spreadsheet_id, "Sites!A2:A")
        sites = [row[0] for row in rows if row]
        return sites

    async def get_site_details(self, site_name: str) -> Dict:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_site_details_sync, site_name)

    def _get_site_details_sync(self, site_name: str) -> Dict:
        rows = self.manager.get_all_values(self.spreadsheet_id, "Sites!A2:D")
        for row in rows:
            if len(row) > 0 and row[0] == site_name:
                # [Name, Lat, Lon, Radius]
                try:
                    return {
                        "name": row[0],
                        "lat": float(row[1]) if len(row) > 1 else 0.0,
                        "lon": float(row[2]) if len(row) > 2 else 0.0,
                        "radius": int(row[3]) if len(row) > 3 else 500
                    }
                except:
                    pass
        return None

    # Implement other methods if interface requires
    async def add_site(self, name: str, lat: float, lon: float, radius: int) -> bool:
        # Not implemented yet via bot
        return False
