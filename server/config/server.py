"""Server configuration management module."""

import os
from dotenv import load_dotenv


class ServerConfig:
    def __init__(self):
        load_dotenv()

        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("FAST_API_PORT", "7860"))
        self.reload: bool = os.getenv("RELOAD", "false").lower() == "true"
