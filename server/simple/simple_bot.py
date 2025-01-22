import asyncio
import os
import argparse
from aiohttp import ClientSession
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from pipecat.audio.vad.silero import SileroVADAnalyzer

# from pipecat.audio.filters.krisp_filter import KrispFilter
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService

# Import config loader
from config.loader import load_config


async def main():
    """Setup and run the simple voice assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple Voice Assistant Bot")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config/simple.json",
        help="Path to config file",
    )
    args = parser.parse_args()

    # Load bot configuration
    config = load_config(args.config)

    async with ClientSession() as session:
        # Initialize transport with VAD and noise filtering
        transport = DailyTransport(
            args.url,
            args.token,
            config.name,
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                # audio_in_filter=KrispFilter(),
            ),
        )

        # Initialize services
        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
        tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-helios-en"
        )
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4")

        # Set up conversation context using config
        messages = [msg.dict() for msg in config.system_messages]
        context = OpenAILLMContext(messages)
        context_aggregator = llm.create_context_aggregator(context)

        # Create pipeline
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                context_aggregator.user(),
                llm,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        # Create pipeline task
        task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            messages.append(
                {"role": "system", "content": "Please introduce yourself to the user."}
            )
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await runner.stop_when_done()

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
