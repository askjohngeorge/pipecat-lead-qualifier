# Centralized Configuration Management Implementation Plan

## Overview
Address redundancy in configuration loading and validation across multiple files by creating a unified configuration system.

## Implementation Steps

1. **Create Config Module**
```python:server/utils/config.py
import os
from dotenv import load_dotenv
from typing import TypedDict

class DailyConfig(TypedDict):
    api_key: str
    api_url: str
    room_url: str

class CalComConfig(TypedDict):
    api_key: str
    event_type_id: int
    event_duration: int
    username: str
    event_slug: str

class AppConfig:
    def __init__(self):
        load_dotenv()
        
        # Validate required vars
        required = {
            "DAILY_API_KEY": os.getenv("DAILY_API_KEY"),
            "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "CALCOM_API_KEY": os.getenv("CALCOM_API_KEY")
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        self.daily: DailyConfig = {
            "api_key": required["DAILY_API_KEY"],
            "api_url": os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
            "room_url": os.getenv("DAILY_SAMPLE_ROOM_URL")
        }
        
        self.calcom: CalComConfig = {
            "api_key": required["CALCOM_API_KEY"],
            "event_type_id": int(os.getenv("CALCOM_EVENT_TYPE_ID", "0")),
            "event_duration": int(os.getenv("CALCOM_EVENT_DURATION", "0")),
            "username": os.getenv("CALCOM_USERNAME", ""),
            "event_slug": os.getenv("CALCOM_EVENT_SLUG", "")
        }
```

2. **Update Existing Files**
```python:server/flow/calcom_api.py
# Replace environment loading with:
from ..utils.config import AppConfig

config = AppConfig()

# Update all os.getenv() calls to use config.calcom attributes
```

3. **Validation Strategy**
- Create pytest fixtures for config validation
- Add unit tests for missing env vars
- Implement type checking in CI pipeline

## Timeline
- Day 1: Implement core config module
- Day 2: Update existing service implementations
- Day 3: Add validation and testing 