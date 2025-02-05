"""Server configuration management module."""

import os
from dotenv import load_dotenv


class ServerConfig:
    def __init__(self):
        load_dotenv()

        # Server settings
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("FAST_API_PORT", "7860"))
        self.reload: bool = os.getenv("RELOAD", "false").lower() == "true"

        # Daily API settings
        self.daily_api_key: str = os.getenv("DAILY_API_KEY")
        self.daily_api_url: str = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")

        # Bot settings
        self.max_bots_per_room: int = int(os.getenv("MAX_BOTS_PER_ROOM", "1"))

        # Validate required settings
        if not self.daily_api_key:
            raise ValueError("DAILY_API_KEY environment variable must be set")
