# Stage 1 Refactoring Implementation Plan

## Objective
Move common boilerplate code from `SimpleBot` and `FlowBot` into shared base classes/utilities while preserving domain-specific logic. First focus on transport setup, pipeline creation, and main execution flow.

## Key Files to Modify
1. `utils/bot_framework.py` (BaseBot enhancements)
2. `server/simple/bot.py`
3. `server/flow/bot.py`
4. New: `utils/run_helpers.py` (for CLI handling)

## Implementation Steps

### 1. Create Unified CLI Runner (`utils/run_helpers.py`)
````python:server/utils/run_helpers.py
import argparse
import asyncio
from aiohttp import ClientSession

async def run_bot(bot_class, config_class):
    """Universal bot runner handling CLI args and lifecycle"""
    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument("-t", "--token", type=str, required=True, help="Daily room token")
    args = parser.parse_args()

    config = config_class()
    bot = bot_class(config)

    async with ClientSession() as session:
        await bot.setup_services()
        await bot.setup_transport(args.url, args.token)
        bot.create_pipeline()
        await bot.start()
````

### 2. Enhance BaseBot with Common Lifecycle Methods
````python:server/utils/bot_framework.py
class BaseBot(ABC):
    async def setup_transport(self, url: str, token: str):
        """Standard transport setup with common event handlers"""
        transport_factory = TransportFactory(self.config)
        self.transport = await self._create_transport(transport_factory, url, token)

        # Common event handlers
        @self.transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await self.runner.stop_when_done()

        await self._setup_transport_impl()

    def create_pipeline(self):
        """Standard pipeline construction"""
        self.pipeline_builder = PipelineBuilder(
            self.transport,
            self.services.stt,
            self.services.tts,
            self.services.llm,
            context=self.context
        )
        pipeline = self.pipeline_builder.add_rtvi(self.rtvi).build()
        
        # Common task configuration
        self.task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                observers=[self.rtvi.observer()],
            )
        )
        self.runner = PipelineRunner()
        self._create_pipeline_impl()
````

### 3. Simplify Bot Implementations

**SimpleBot Changes:**
````python:server/simple/bot.py
class SimpleBot(BaseBot):
    # Keep domain-specific items:
    # - __init__ with messages
    # - _setup_services_impl
    # - _create_transport
    # - _handle_first_participant

# Remove all main() boilerplate and replace with:
async def main():
    from utils.run_helpers import run_bot
    from utils.config import AppConfig
    await run_bot(SimpleBot, AppConfig)
````

**FlowBot Changes:**
````python:server/flow/bot.py
class FlowBot(BaseBot):
    # Keep domain-specific items:
    # - __init__ with flow_config
    # - _setup_services_impl
    # - _create_transport
    # - _create_pipeline_impl (flow manager)
    # - flow handler functions

# Remove all main() boilerplate and replace with:
async def main():
    from utils.run_helpers import run_bot
    from utils.config import AppConfig
    await run_bot(FlowBot, AppConfig)
````

### 4. Common Transport Setup Consolidation
Move these to BaseBot:
- Signal handling
- Participant left event
- Cleanup logic
- RTVI client ready handler

### 5. Preserve Extension Points
Maintain these abstract methods for bot-specific implementations:
```python
@abstractmethod
async def _setup_services_impl(self): ...
@abstractmethod
async def _create_transport(self, factory, url: str, token: str): ...
@abstractmethod
async def _handle_first_participant(self): ...
```