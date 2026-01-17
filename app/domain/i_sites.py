from abc import ABC, abstractmethod
from typing import List

class ISitesRepository(ABC):
    @abstractmethod
    async def get_all_sites(self) -> List[str]:
        pass
