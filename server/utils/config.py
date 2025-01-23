"""Configuration management module for server components."""

import os
from typing import TypedDict, Literal, NotRequired
from dotenv import load_dotenv


class DailyConfig(TypedDict):
    api_key: str
    api_url: str
    room_url: NotRequired[str]


class CalComConfig(TypedDict):
    api_key: str
    event_type_id: int
    event_duration: int
    username: str
    event_slug: str


BotType = Literal["simple", "flow"]


class AppConfig:
    def __init__(self):
        load_dotenv()

        # Validate required vars
        required = {
            "DAILY_API_KEY": os.getenv("DAILY_API_KEY"),
            "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "CALCOM_API_KEY": os.getenv("CALCOM_API_KEY"),
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        self.daily: DailyConfig = {
            "api_key": required["DAILY_API_KEY"],
            "api_url": os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        }

        # Add room_url only if it's provided
        if room_url := os.getenv("DAILY_SAMPLE_ROOM_URL"):
            self.daily["room_url"] = room_url

        self.calcom: CalComConfig = {
            "api_key": required["CALCOM_API_KEY"],
            "event_type_id": int(os.getenv("CALCOM_EVENT_TYPE_ID", "0")),
            "event_duration": int(os.getenv("CALCOM_EVENT_DURATION", "0")),
            "username": os.getenv("CALCOM_USERNAME", ""),
            "event_slug": os.getenv("CALCOM_EVENT_SLUG", ""),
        }

        # Server configuration
        self._bot_type: BotType = os.getenv("BOT_TYPE", "simple")
        if self._bot_type not in ("simple", "flow"):
            self._bot_type = "simple"  # Default to flow bot if invalid value

    @property
    def deepgram_api_key(self) -> str:
        return os.environ["DEEPGRAM_API_KEY"]

    @property
    def openai_api_key(self) -> str:
        return os.environ["OPENAI_API_KEY"]

    @property
    def bot_type(self) -> BotType:
        return self._bot_type

    @bot_type.setter
    def bot_type(self, value: BotType):
        if value not in ("simple", "flow"):
            raise ValueError("Bot type must be either 'simple' or 'flow'")
        self._bot_type = value
