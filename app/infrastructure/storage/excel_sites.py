import pandas as pd
import os
import asyncio
from typing import Dict, Any, List

class ExcelSitesRepository:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.sheet_name = "Sites"
        self._ensure_file()

    def _ensure_file(self):
        # Already handled by main initializer usually, but for safety:
        if not os.path.exists(self.filepath):
             # Just create basic if missing
             pass

    async def get_all_sites(self) -> List[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_sync)

    def _read_sync(self) -> List[str]:
        try:
            df = pd.read_excel(self.filepath, sheet_name=self.sheet_name)
            return df["Site Name"].dropna().astype(str).tolist()
        except:
            return []
