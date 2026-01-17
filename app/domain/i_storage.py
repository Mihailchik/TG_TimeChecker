from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class IStateStorage(ABC):
    @abstractmethod
    def get_active_shift(self, user_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all_active_shifts(self) -> List[Dict[str, Any]]:
        pass
    
    # New granular methods
    @abstractmethod
    def create_shift(self, user_id: int) -> int:
        pass

    @abstractmethod
    def update_shift(self, shift_id: int, data: Dict[str, Any]):
        pass

    @abstractmethod
    def remove_active_shift(self, user_id: int) -> bool:
        pass

class IHistoryStorage(ABC):
    @abstractmethod
    async def log_completed_shift(self, shift_data: Dict[str, Any]) -> bool:
        pass
