from datetime import datetime
from typing import Dict, Optional

from ai_companion.core.schedules import (
    SUNDAY_SCHEDULE,
    MONDAY_SCHEDULE,
    TUESDAY_SCHEDULE,
    WEDNESDAY_SCHEDULE,
    THURSDAY_SCHEDULE,
    FRIDAY_SCHEDULE,
    SATURDAY_SCHEDULE
)

class ScheduleContextGenerator:
    """Class to generate context about Tela's current activity based on schedule"""
    SCHEDULE = {
        0: MONDAY_SCHEDULE,
        1: TUESDAY_SCHEDULE,
        2: WEDNESDAY_SCHEDULE,
        3: THURSDAY_SCHEDULE,
        4: FRIDAY_SCHEDULE,
        5: SATURDAY_SCHEDULE,
        6: SUNDAY_SCHEDULE
    }

    @staticmethod
    def _parse_time_range(time_range: str) -> tuple[datetime.time, datetime.time]:
        """Parse a time range string e.g ('06:00-07:00') into start and end times"""
        start_str, end_str = time_range.split("-")
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        return start_time, end_time
    
    @classmethod
    def get_current_activity(cls) -> Optional[str]:
        """Get Tela's current activity based on the currrent time and day of the week.
        
        Returns:
            str: Description of current activity or None if no current matching time slot is found.
        """
        current_time = datetime.time()
        current_day = datetime.weekday()

        schedule = cls.SCHEDULE.get(current_day, {})

        for time_range, activity in schedule.items():
            start_time, end_time = cls._parse_time_range(time_range)

            if start_time > end_time:
                if start_time <= current_time <= end_time:
                    return activity
            else:
                if start_time <= current_time <= end_time:
                    return activity
        
        return None
    
    @classmethod
    def get_schedule_for_day(cls, day: int) -> Dict[str, str]:
        """Get the complete schedule for a specific day.
        
        Args:
            day: Day of week as integer(0 = Monday, 6 = Sunday)
        
        Returns:
            Dict[str, str]: Schedule for the specific day
        """
        return cls.SCHEDULE.get(day, {})
