# Base Bot Class Implementation Plan

## Overview
Create abstract base class for common bot functionality across implementations.

## Implementation

1. **Base Class Structure** (`server/bot/base.py`)
```python
from abc import ABC, abstractmethod
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask

class BaseBot(ABC):
    def __init__(self, config):
        self.config = config
        self.runner = PipelineRunner()
        self.transport = self._create_transport()
        self._setup_services()
        self.pipeline = self._create_pipeline()
        self.task = PipelineTask(self.pipeline)

    @abstractmethod
    def _create_transport(self):
        """Create transport implementation"""
        
    @abstractmethod
    def _setup_services(self):
        """Initialize STT/TTS/LLM services"""
        
    @abstractmethod
    def _create_pipeline(self) -> Pipeline:
        """Build bot-specific pipeline"""

    # Common event handlers
    async def _on_participant_joined(self, transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        
    async def _on_participant_left(self, transport, participant, reason):
        await self.runner.stop_when_done()

    def register_handlers(self):
        """Register common event handlers"""
        self.transport.event_handler("on_first_participant_joined")(
            self._on_participant_joined
        )
        self.transport.event_handler("on_participant_left")(
            self._on_participant_left
        )
```

2. **Flow Bot Implementation** (`server/flow/bot.py`)
```python
from .bot.base import BaseBot

class FlowBot(BaseBot):
    def _create_transport(self):
        return TransportFactory(self.config).create_lead_qualifier_transport()

    def _setup_services(self):
        self.stt = DeepgramSTTService(api_key=self.config.deepgram_api_key)
        self.tts = DeepgramTTSService(api_key=self.config.deepgram_api_key)
        self.llm = OpenAILLMService(api_key=self.config.openai_api_key)

    def _create_pipeline(self):
        return PipelineBuilder(self.transport, self.stt, self.tts, self.llm)
            .add_rtvi(rtvi_config)
            .build()
```

3. **Validation Strategy**
- Verify event handler consistency across bot types
- Test base class error handling
- Ensure template methods enforce implementation

## Migration Timeline
- Day 1: Base class implementation
- Day 2: Bot migrations
- Day 3: Handler validation 