"""Cal.com API integration service.

This module provides a typed interface to the Cal.com API v2, handling:
- Availability checking
- Booking creation and management
- Time slot formatting and timezone conversion

The service is configured through environment variables and provides
robust error handling and retry mechanisms for API operations.
"""

import os
import json
from typing import TypedDict, Optional, List, Dict, Tuple
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv
from loguru import logger
from zoneinfo import ZoneInfo

# Load environment variables
load_dotenv()

# Environment validation
required_env_vars = [
    "CALCOM_API_KEY",
    "CALCOM_EVENT_TYPE_ID",
    "CALCOM_EVENT_DURATION",
    "CALCOM_USERNAME",
    "CALCOM_EVENT_SLUG",
]

for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} is required")


# Configuration
class Config:
    BASE_URL = "https://api.cal.com/v2"
    API_KEY = os.getenv("CALCOM_API_KEY")
    EVENT_TYPE_ID = int(os.getenv("CALCOM_EVENT_TYPE_ID", "0"))
    EVENT_DURATION = int(os.getenv("CALCOM_EVENT_DURATION", "0"))
    USERNAME = os.getenv("CALCOM_USERNAME")
    EVENT_SLUG = os.getenv("CALCOM_EVENT_SLUG")


# Type definitions
class Slot(TypedDict):
    time: str
    attendees: Optional[int]
    bookingId: Optional[str]


class AvailabilityResponse(TypedDict):
    success: bool
    availability: Optional[Dict[str, List[Slot]]]
    message: Optional[str]
    error: Optional[str]


class BookingDetails(TypedDict):
    name: str
    email: str
    company: str
    phone: str
    timezone: str
    notes: Optional[str]
    startTime: str


class BookingResponse(TypedDict):
    success: bool
    booking: Optional[dict]
    message: Optional[str]
    error: Optional[str]


class TimeSlot(TypedDict):
    date: str  # e.g., "2024-01-19"
    time: str  # e.g., "10:00 AM"
    datetime: str  # Full ISO string
    is_morning: bool


class FormattedAvailability(TypedDict):
    dates: List[str]
    slots_by_date: Dict[str, List[TimeSlot]]


class CalComAPI:
    def __init__(self):
        self.config = Config()
        self._last_availability_check: Optional[FormattedAvailability] = None

    def _format_time(self, dt_str: str, timezone: str = "UTC") -> Tuple[str, str, bool]:
        """Format datetime string into date and time components."""
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if timezone != "UTC":
            dt = dt.astimezone(ZoneInfo(timezone))

        date = dt.strftime("%A, %B %d")  # e.g., "Thursday, January 19"
        time = dt.strftime("%I:%M %p")  # e.g., "10:00 AM"
        is_morning = dt.hour < 12

        return date, time, is_morning

    def _parse_availability(
        self, slots_data: Dict[str, List[Slot]], timezone: str = "UTC"
    ) -> FormattedAvailability:
        """Parse and format the availability data into a more usable structure."""
        formatted: Dict[str, List[TimeSlot]] = {}

        for date_str, slots in slots_data.items():
            for slot in slots:
                date, time, is_morning = self._format_time(slot["time"], timezone)

                if date not in formatted:
                    formatted[date] = []

                formatted[date].append(
                    {
                        "date": date,
                        "time": time,
                        "datetime": slot["time"],
                        "is_morning": is_morning,
                    }
                )

        # Sort dates
        dates = sorted(formatted.keys(), key=lambda x: datetime.strptime(x, "%A, %B %d"))

        return {"dates": dates, "slots_by_date": formatted}

    def get_morning_afternoon_slots(
        self, date: str
    ) -> Tuple[Optional[TimeSlot], Optional[TimeSlot]]:
        """Get a morning and afternoon slot for a given date from the last availability check."""
        if not self._last_availability_check:
            return None, None

        slots = self._last_availability_check["slots_by_date"].get(date, [])
        morning_slot = next((slot for slot in slots if slot["is_morning"]), None)
        afternoon_slot = next((slot for slot in slots if not slot["is_morning"]), None)

        return morning_slot, afternoon_slot

    async def get_availability(
        self, days: int = 5, timezone: str = "UTC", retry_count: int = 2
    ) -> AvailabilityResponse:
        """Fetch available time slots for the configured event type with retries."""
        last_error = None

        for attempt in range(retry_count):
            try:
                start_time = datetime.now().isoformat()
                end_time = (datetime.now() + timedelta(days=days)).isoformat()

                params = {
                    "startTime": start_time,
                    "endTime": end_time,
                    "eventTypeId": str(self.config.EVENT_TYPE_ID),
                    "eventTypeSlug": self.config.EVENT_SLUG,
                    "duration": str(self.config.EVENT_DURATION),
                    "usernameList[]": self.config.USERNAME,
                }

                logger.info(f"Cal.com Availability Request (Attempt {attempt + 1}/{retry_count}):")
                logger.info(f"URL: {self.config.BASE_URL}/slots/available")
                logger.info(f"Params: {json.dumps(params, indent=2)}")
                logger.info(
                    f"Headers: {json.dumps({'Authorization': 'Bearer [REDACTED]', 'Content-Type': 'application/json'}, indent=2)}"
                )

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.config.BASE_URL}/slots/available",
                        params=params,
                        headers={
                            "Authorization": f"Bearer {self.config.API_KEY}",
                            "Content-Type": "application/json",
                        },
                    ) as response:
                        if not response.ok:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to fetch availability (Attempt {attempt + 1}): {error_text}"
                            )
                            last_error = f"Failed to fetch availability: {response.status}"
                            continue

                        data = await response.json()
                        if data.get("status") == "success" and "slots" in data.get("data", {}):
                            logger.success(
                                f"Successfully fetched availability (Attempt {attempt + 1})"
                            )
                            # Store the formatted availability for later use
                            self._last_availability_check = self._parse_availability(
                                data["data"]["slots"], timezone
                            )
                            return {
                                "success": True,
                                "availability": data["data"]["slots"],
                            }

                        logger.error(
                            f"Invalid response format from Cal.com API (Attempt {attempt + 1})"
                        )
                        last_error = "Invalid response format"
                        continue

            except Exception as e:
                logger.exception(f"Failed to fetch availability (Attempt {attempt + 1}): {str(e)}")
                last_error = f"Failed to fetch availability: {str(e)}"
                continue

        return {
            "success": False,
            "error": last_error or "Failed to fetch availability after all retries",
        }

    async def create_booking(
        self, details: BookingDetails, retry_count: int = 2
    ) -> BookingResponse:
        """Create a new booking with the provided details with retries."""
        last_error = None

        for attempt in range(retry_count):
            try:
                booking_data = {
                    "eventTypeId": self.config.EVENT_TYPE_ID,
                    "start": details["startTime"],
                    "attendee": {
                        "name": details["name"],
                        "email": details["email"],
                        "timeZone": details["timezone"],
                    },
                    "bookingFieldsResponses": {
                        "company": details["company"],
                        "phone": details["phone"],
                    },
                }

                if details.get("notes"):
                    booking_data["bookingFieldsResponses"]["notes"] = details["notes"]

                logger.info(f"Cal.com Booking Request (Attempt {attempt + 1}/{retry_count}):")
                logger.info(f"URL: https://api.cal.com/v2/bookings")
                logger.info(f"Data: {json.dumps(booking_data, indent=2)}")
                logger.info(
                    f"Headers: {json.dumps({'Authorization': 'Bearer [REDACTED]', 'Content-Type': 'application/json', 'cal-api-version': '2024-08-13'}, indent=2)}"
                )

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.cal.com/v2/bookings",
                        headers={
                            "Authorization": f"Bearer {self.config.API_KEY}",
                            "Content-Type": "application/json",
                            "cal-api-version": "2024-08-13",
                        },
                        json=booking_data,
                    ) as response:
                        if not response.ok:
                            error_text = await response.text()
                            logger.error(
                                f"Failed to create booking (Attempt {attempt + 1}): {error_text}"
                            )
                            last_error = f"Failed to create booking: {response.status}"
                            continue

                        booking = await response.json()
                        logger.success(f"Successfully created booking (Attempt {attempt + 1})")
                        return {"success": True, "booking": booking}

            except Exception as e:
                logger.exception(f"Failed to create booking (Attempt {attempt + 1}): {str(e)}")
                last_error = f"Failed to create booking: {str(e)}"
                continue

        return {
            "success": False,
            "error": last_error or "Failed to create booking after all retries",
        }


# Example usage:
async def main():
    api = CalComAPI()

    # Get availability
    availability = await api.get_availability(days=5)
    print(json.dumps(availability, indent=2))

    # Example booking (uncomment to test)
    # booking_details = {
    #     'name': 'Test User',
    #     'email': 'test@example.com',
    #     'company': 'Test Company',
    #     'phone': '+1234567890',
    #     'timezone': 'America/New_York',
    #     'startTime': '2024-01-20T10:00:00Z'
    # }
    # booking = await api.create_booking(booking_details)
    # print(json.dumps(booking, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
