from datetime import datetime
from app.domain.i_calculator import ICalculator

class StandardTimeCalculator(ICalculator):
    def calculate_duration(self, start_time: datetime, end_time: datetime) -> float:
        duration = end_time - start_time
        return round(duration.total_seconds() / 3600, 2)
