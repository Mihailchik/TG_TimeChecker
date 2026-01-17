from abc import ABC, abstractmethod
from datetime import datetime

class ICalculator(ABC):
    """Interface for calculation logic."""
    
    @abstractmethod
    def calculate_duration(self, start_time: datetime, end_time: datetime) -> float:
        """Returns duration in hours."""
        pass
