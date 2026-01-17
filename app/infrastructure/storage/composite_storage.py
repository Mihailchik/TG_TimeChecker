from typing import List, Dict, Any
import asyncio
from app.domain.i_storage import IHistoryStorage

class CompositeHistoryStorage(IHistoryStorage):
    """
    Writes to multiple storages in parallel.
    """
    def __init__(self, storages: List[IHistoryStorage]):
        self.storages = storages

    async def log_completed_shift(self, shift_data: Dict[str, Any]) -> bool:
        success = True
        for storage in self.storages:
            try:
                # Some storages might be async, some sync?
                # Assume all implement correct interface.
                # If interface says async, we await.
                if asyncio.iscoroutinefunction(storage.log_completed_shift):
                     res = await storage.log_completed_shift(shift_data)
                else:
                    res = storage.log_completed_shift(shift_data)
                
                if not res:
                    success = False
            except Exception as e:
                print(f"Storage Error: {e}")
                success = False
        return success

    async def log_start_shift(self, shift_data: Dict[str, Any]) -> Any:
        result_row = None
        for storage in self.storages:
            if hasattr(storage, 'log_start_shift'):
                try:
                    res = None
                    if asyncio.iscoroutinefunction(storage.log_start_shift):
                         res = await storage.log_start_shift(shift_data)
                    else:
                         res = storage.log_start_shift(shift_data)
                    
                    if res is not None and result_row is None:
                        result_row = res
                except Exception:
                    pass
        return result_row

    async def update_shift_end(self, row_num: int, shift_data: Dict[str, Any]) -> bool:
        success = True
        for storage in self.storages:
            if hasattr(storage, 'update_shift_end'):
                try:
                    if asyncio.iscoroutinefunction(storage.update_shift_end):
                         await storage.update_shift_end(row_num, shift_data)
                    else:
                         storage.update_shift_end(row_num, shift_data)
                except Exception:
                    success = False
        return success
