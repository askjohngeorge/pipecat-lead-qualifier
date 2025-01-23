# Daily API Consolidation Implementation Plan

## Overview
Centralize Daily API configuration and room management to eliminate duplicate code in runner.py and server.py.

## Implementation Steps

1. **Create DailyAPI Utility Class**
```python:server/utils/daily.py
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper

class DailyAPI:
    def __init__(self, config):
        self.helper = DailyRESTHelper(
            daily_api_key=config.daily["api_key"],
            daily_api_url=config.daily["api_url"],
            aiohttp_session=aiohttp.ClientSession()
        )

    async def create_room(self):
        return await self.helper.create_room()

    async def get_token(self, room_url, expiry=3600):
        return await self.helper.get_token(room_url, expiry)

    async def delete_room(self, room_url):
        return await self.helper.delete_room(room_url)
```

2. **Update Existing Implementations**
```python:server/runner.py
# Replace configure() with:
from ..utils.daily import DailyAPI
from ..utils.config import AppConfig

config = AppConfig()

async def configure(session):
    daily = DailyAPI(config)
    token = await daily.get_token(config.daily["room_url"])
    return (config.daily["room_url"], token)
```

3. **Error Handling**
- Add retry decorator for API calls
- Implement consistent error logging
- Create standardized response format

## Migration Strategy
1. Phase 1: Implement new utility class
2. Phase 2: Update server.py and runner.py
3. Phase 3: Deprecate old implementations

## Timeline
- Day 1: Core utility implementation
- Day 2: Server/Runner migration
- Day 3: Error handling improvements 