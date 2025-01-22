# Building a Simple Voice AI Assistant with Pipecat

This guide explains how to build a basic voice AI assistant using Pipecat. This implementation uses a simple monolithic approach with a single system prompt.

## Environment Setup

First, set up your environment variables in a `.env` file:

```bash
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
DAILY_API_KEY=your_daily_api_key
DAILY_SAMPLE_ROOM_URL=your_daily_room_url
```

## Required Imports

```python
import asyncio
import os
import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.filters.krisp_filter import KrispFilter
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer
```

## Configuring Daily Transport

The Daily transport handles WebRTC communication. Initialize it with voice activity detection (VAD) and noise filtering:

```python
transport = DailyTransport(
    room_url,
    token,
    "Voice Assistant",
    DailyParams(
        audio_out_enabled=True,
        vad_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
        vad_audio_passthrough=True,
        audio_in_filter=KrispFilter(),
    ),
)
```

## Setting Up Services

Initialize the speech-to-text, text-to-speech, and language model services:

```python
stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
tts = DeepgramTTSService(
    api_key=os.getenv("DEEPGRAM_API_KEY"), 
    voice="aura-helios-en"
)
llm = OpenAILLMService(
    api_key=os.getenv("OPENAI_API_KEY"), 
    model="gpt-4o"
)
```

## Creating the Context

Set up the conversation context with a simple system prompt:

```python
messages = [
    {
        "role": "system",
        "content": "You are a helpful voice assistant. Your responses will be converted to audio.",
    }
]

context = OpenAILLMContext(messages)
context_aggregator = llm.create_context_aggregator(context)
```

## Building the Pipeline

Create a pipeline that connects all components:

```python
pipeline = Pipeline([
    transport.input(),         # Receive user audio
    stt,                      # Convert speech to text
    context_aggregator.user(), # Add user input to context
    llm,                      # Generate response
    tts,                      # Convert response to speech
    transport.output(),       # Send audio response
    context_aggregator.assistant(), # Add assistant response to context
])
```

## Setting Up the Task

Create a pipeline task with interruption support:

```python
task = PipelineTask(
    pipeline,
    PipelineParams(
        allow_interruptions=True,
        enable_metrics=True,
        enable_usage_metrics=True,
    ),
)
```

## Handling Events

Set up event handlers for participant joining and leaving:

```python
@transport.event_handler("on_first_participant_joined")
async def on_first_participant_joined(transport, participant):
    # Start the conversation
    messages.append({"role": "system", "content": "Please introduce yourself to the user."})
    await task.queue_frames([context_aggregator.user().get_context_frame()])

@transport.event_handler("on_participant_left")
async def on_participant_left(transport, participant, reason):
    await task.queue_frame(EndFrame())
```

## Running the Assistant

Create the main function to run the assistant:

```python
async def main():
    async with aiohttp.ClientSession() as session:
        # Get room configuration
        (room_url, token) = await configure(session)
        
        # Initialize all components (as shown above)
        # ...

        # Create and run the pipeline
        runner = PipelineRunner()
        await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())
```

## Room Configuration Helper

Create a separate `runner.py` file to handle Daily room configuration:

```python
async def configure(aiohttp_session: aiohttp.ClientSession):
    url = os.getenv("DAILY_SAMPLE_ROOM_URL")
    key = os.getenv("DAILY_API_KEY")

    if not url or not key:
        raise Exception("Missing Daily configuration")

    daily_rest_helper = DailyRESTHelper(
        daily_api_key=key,
        daily_api_url="https://api.daily.co/v1",
        aiohttp_session=aiohttp_session,
    )

    # Create token with 1-hour expiry
    token = await daily_rest_helper.get_token(url, 60 * 60)
    return (url, token)
```

## Running the Bot

To run the bot:

1. Ensure all environment variables are set in your `.env` file
2. Run the script: `python your_bot_file.py`

The bot will connect to the specified Daily room and begin listening for participants. When someone joins, it will introduce itself and begin the conversation.