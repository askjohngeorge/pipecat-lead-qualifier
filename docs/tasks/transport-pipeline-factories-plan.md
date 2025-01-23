# Transport & Pipeline Factories Implementation Plan

## Overview
Create factory patterns for DailyTransport and Pipeline setup to eliminate duplicate code across bot implementations.

## Implementation Steps

1. **Transport Factory**
```python:server/utils/transports.py
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer

def create_daily_transport(room_url: str, token: str, bot_name: str):
    return DailyTransport(
        room_url,
        token,
        bot_name,
        DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True
        )
    )
```

2. **Pipeline Factory**
```python:server/utils/pipelines.py
from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext

def create_core_pipeline(llm: OpenAILLMService, transport, stt, tts):
    context = OpenAILLMContext()
    context_aggregator = llm.create_context_aggregator(context)
    
    return Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])
```

3. **Update Bot Implementations**
```python:server/flow/bot.py
# Replace transport setup with:
from ..utils.transports import create_daily_transport

transport = create_daily_transport(room_url, None, "Lead Qualification Bot")

# Replace pipeline setup with:
from ..utils.pipelines import create_core_pipeline

pipeline = create_core_pipeline(llm, transport, stt, tts)
```

## Validation Plan
- Create integration tests for factory outputs
- Verify audio/video metrics consistency
- Load test with different bot configurations

## Timeline
- Day 1: Factory implementations
- Day 2: Bot implementation updates
- Day 3: Testing and validation 