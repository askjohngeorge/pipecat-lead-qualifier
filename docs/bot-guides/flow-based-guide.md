# Building a Flow-Based Voice AI Assistant with Pipecat

This guide explains how to build a voice AI assistant using Pipecat's flow-based architecture. This implementation allows for structured conversation flows with defined states and transitions.

## Environment Setup

Set up your environment variables in a `.env` file:

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
from aiohttp import ClientSession
from dotenv import load_dotenv

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat_flows import FlowManager, FlowArgs, FlowConfig, FlowResult
```

## Defining the Flow Configuration

Create a flow configuration that defines conversation states and transitions:

```python
flow_config: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a helpful voice assistant. Your responses will be converted to audio.",
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Greet the user warmly.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_user_response",
                        "description": "Process user's response",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                        "transition_to": "main_conversation",
                    },
                },
            ],
        },
        "main_conversation": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Engage in conversation with the user.",
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "handle_conversation",
                        "description": "Process conversation",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                        "transition_to": "end_conversation",
                    },
                },
            ],
        },
        "end_conversation": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "End the conversation politely.",
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
}
```

## Setting Up Services

Initialize the necessary services:

```python
# Initialize transport with VAD
transport = DailyTransport(
    room_url,
    None,
    "Flow-Based Assistant",
    DailyParams(
        audio_out_enabled=True,
        vad_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
        vad_audio_passthrough=True,
    ),
)

# Initialize STT, TTS, and LLM services
stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
tts = DeepgramTTSService(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    voice="aura-helios-en"
)
llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

# Set up context aggregation
context = OpenAILLMContext()
context_aggregator = llm.create_context_aggregator(context)
```

## Building the Pipeline

Create the pipeline connecting all components:

```python
pipeline = Pipeline([
    transport.input(),
    stt,
    context_aggregator.user(),
    llm,
    tts,
    transport.output(),
    context_aggregator.assistant(),
])

# Create pipeline task
task = PipelineTask(
    pipeline,
    PipelineParams(
        allow_interruptions=True,
        enable_metrics=True,
        enable_usage_metrics=True,
    ),
)
```

## Initializing Flow Manager

Set up the flow manager to handle conversation states:

```python
flow_manager = FlowManager(
    task=task,
    llm=llm,
    context_aggregator=context_aggregator,
    tts=tts,
    flow_config=flow_config,
)
```

## Event Handling

Set up event handlers for participant management:

```python
@transport.event_handler("on_first_participant_joined")
async def on_first_participant_joined(transport, participant):
    await transport.capture_participant_transcription(participant["id"])
    await flow_manager.initialize()
    await task.queue_frames([context_aggregator.user().get_context_frame()])

@transport.event_handler("on_participant_left")
async def on_participant_left(transport, participant, reason):
    await runner.stop_when_done()
```

## Main Function

Create the main function to run the assistant:

```python
async def main():
    async with ClientSession() as session:
        # Get room configuration
        (room_url, _) = await configure(session)
        
        # Initialize all components (as shown above)
        # ...

        # Create and run the pipeline
        runner = PipelineRunner()
        await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())
```

## Room Configuration

Use the provided `bot_runner.py` for Daily room configuration:

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

    token = await daily_rest_helper.get_token(url, 60 * 60)  # 1-hour expiry
    return (url, token)
```

## Running the Bot

To run the flow-based bot:

1. Ensure all environment variables are set in your `.env` file
2. Run the script: `python your_flow_bot.py`

The bot will connect to the specified Daily room and begin executing the conversation flow when a participant joins.

## Key Differences from Simple Implementation

The main differences from the simple implementation are:

1. Structured conversation flow using the `FlowConfig` object
2. State-based conversation management
3. Defined transitions between conversation states
4. Separation of system prompts by conversation phase
5. Built-in support for function calling between states