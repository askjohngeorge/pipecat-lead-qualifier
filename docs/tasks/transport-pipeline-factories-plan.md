# Transport & Pipeline Factories Implementation Plan

## Overview
Create factory patterns for DailyTransport and Pipeline setup to eliminate duplicate code across bot implementations.

## 1. Transport Factory Implementation
```python:server/utils/transports.py
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from ..config import AppConfig

class TransportFactory:
    def __init__(self, config: AppConfig):
        self._default_params = DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True
        )
        
    def create_lead_qualifier_transport(self, room_url: str, token: str):
        return DailyTransport(
            room_url,
            token,
            "Lead Qualification Bot",
            self._default_params
        )
    
    def create_simple_assistant_transport(self, room_url: str, token: str):
        return DailyTransport(
            room_url,
            token,
            "Voice Assistant",
            self._default_params
        )
```

## 2. Pipeline Builder Implementation
```python:server/utils/pipelines.py
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

class PipelineBuilder:
    def __init__(self, transport, stt, tts, llm):
        self._transport = transport
        self._stt = stt
        self._tts = tts
        self._llm = llm
        self._processors = []
        
    def add_rtvi(self, rtvi_config):
        self._processors.append(rtvi_config)
        return self
        
    def build(self):
        context = OpenAILLMContext()
        context_aggregator = self._llm.create_context_aggregator(context)
        
        core_processors = [
            self._transport.input(),
            self._stt,
            context_aggregator.user(),
            self._llm,
            self._tts,
            self._transport.output(),
            context_aggregator.assistant(),
        ]
        
        return Pipeline(self._processors + core_processors)
```

## 3. Bot Implementation Updates
**Flow Bot** (`server/flow/bot.py`):
```python
from ..utils.transports import TransportFactory
from ..utils.pipelines import PipelineBuilder

# Transport setup
transport = TransportFactory(config).create_lead_qualifier_transport(args.url, args.token)

# Pipeline setup
pipeline = (
    PipelineBuilder(transport, stt, tts, llm)
    .add_rtvi(rtvi)
    .build()
)
```

## 4. Validation Strategy
1. **Integration Tests**
- Verify transport audio/video metrics match previous implementations
- Validate pipeline processor order through instrumentation

2. **Load Testing**
- Compare WebSocket connections per bot type
- Measure memory usage across bot instances

3. **Validation Metrics**
```python
assert transport.params.vad_enabled == True
assert isinstance(pipeline.processors[0], DailyInput)
assert any(isinstance(p, RTVIProcessor) for p in pipeline.processors)  # Flow bot only
```

## Timeline
- Day 1: Factory implementations and base tests
- Day 2: Bot migrations and integration testing
- Day 3: Performance benchmarking and documentation 