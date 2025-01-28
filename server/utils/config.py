"""Configuration management module for server components."""

import os
from typing import TypedDict, Literal, NotRequired
from dotenv import load_dotenv


class DailyConfig(TypedDict):
    api_key: str
    api_url: str
    room_url: NotRequired[str]


BotType = Literal["simple", "flow"]


class AppConfig:
    def __init__(self):
        load_dotenv()

        # Validate required vars
        required = {
            "DAILY_API_KEY": os.getenv("DAILY_API_KEY"),
            "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
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

        # Server configuration
        self._bot_type: BotType = os.getenv("BOT_TYPE", "simple")
        if self._bot_type not in ("simple", "flow"):
            self._bot_type = "simple"  # Default to simple bot if invalid value

    @property
    def deepgram_api_key(self) -> str:
        return os.environ["DEEPGRAM_API_KEY"]

    @property
    def openai_api_key(self) -> str:
        return os.environ["OPENAI_API_KEY"]

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def bot_type(self) -> BotType:
        return self._bot_type

    @bot_type.setter
    def bot_type(self, value: BotType):
        self._bot_type = value
