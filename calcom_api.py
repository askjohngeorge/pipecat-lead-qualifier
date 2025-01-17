import os
import json
from typing import TypedDict, Optional, List, Dict, Union
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv
from loguru import logger

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


class CalComAPI:
    def __init__(self):
        self.config = Config()

    async def get_availability(self, days: int = 5) -> AvailabilityResponse:
        """Fetch available time slots for the configured event type."""
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

            logger.info("Cal.com Availability Request:")
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
                        logger.error(f"Failed to fetch availability: {error_text}")
                        return {
                            "success": False,
                            "error": f"Failed to fetch availability: {response.status}",
                        }

                    data = await response.json()
                    if data.get("status") == "success" and "slots" in data.get(
                        "data", {}
                    ):
                        logger.success("Successfully fetched availability")
                        return {"success": True, "availability": data["data"]["slots"]}
                    logger.error("Invalid response format from Cal.com API")
                    return {"success": False, "error": "Invalid response format"}

        except Exception as e:
            logger.exception(f"Failed to fetch availability: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch availability: {str(e)}",
            }

    async def create_booking(self, details: BookingDetails) -> BookingResponse:
        """Create a new booking with the provided details."""
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

            logger.info("Cal.com Booking Request:")
            logger.info(f"URL: {self.config.BASE_URL}/bookings")
            logger.info(f"Data: {json.dumps(booking_data, indent=2)}")
            logger.info(
                f"Headers: {json.dumps({'Authorization': 'Bearer [REDACTED]', 'Content-Type': 'application/json', 'cal-api-version': '2024-08-13'}, indent=2)}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.config.BASE_URL}/bookings",
                    headers={
                        "Authorization": f"Bearer {self.config.API_KEY}",
                        "Content-Type": "application/json",
                        "cal-api-version": "2024-08-13",
                    },
                    json=booking_data,
                ) as response:
                    if not response.ok:
                        error_text = await response.text()
                        logger.error(f"Failed to create booking: {error_text}")
                        return {
                            "success": False,
                            "error": f"Failed to create booking: {response.status}",
                        }

                    booking = await response.json()
                    logger.success("Successfully created booking")
                    return {"success": True, "booking": booking}

        except Exception as e:
            logger.exception(f"Failed to create booking: {str(e)}")
            return {"success": False, "error": f"Failed to create booking: {str(e)}"}


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
