import asyncio
import os
import argparse
from aiohttp import ClientSession
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat_flows import FlowManager

# Import config loader
from config.loader import load_config


async def run_simple_bot(config, transport, task, context_aggregator):
    """Run the bot in simple mode."""

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        await task.queue_frames([context_aggregator.user().get_context_frame()])


async def run_flow_bot(config, transport, task, llm, context_aggregator, tts):
    """Run the bot in flow mode."""
    # Initialize RTVI processor for function handling
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Initialize flow manager
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        tts=tts,
        flow_config=config.flow_config,
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        await flow_manager.initialize()
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    return rtvi


async def main(args_list=None):
    """Setup and run the voice assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Unified Voice Assistant Bot")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to config file",
    )

    # Parse either provided args or sys.argv
    args = parser.parse_args(args_list)

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
            ),
        )

        # Initialize services
        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
        tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"), voice="aura-helios-en"
        )
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4")

        # Set up initial context based on config type
        if config.type == "simple":
            messages = [msg.dict() for msg in config.system_messages]
            context = OpenAILLMContext(messages)
        else:  # flow type
            context = OpenAILLMContext()  # Flow manager will handle messages

        context_aggregator = llm.create_context_aggregator(context)

        # Initialize pipeline components
        pipeline_components = [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]

        # Add RTVI processor for flow type
        rtvi = None
        if config.type == "flow":
            rtvi = await run_flow_bot(
                config, transport, None, llm, context_aggregator, tts
            )
            pipeline_components.insert(1, rtvi)  # Add after transport.input()

        # Create pipeline
        pipeline = Pipeline(pipeline_components)

        # Create pipeline task with appropriate parameters
        task_params = PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        )

        if config.type == "flow":
            task_params.observers = [rtvi.observer()]

        task = PipelineTask(pipeline, task_params)

        # Initialize appropriate bot type
        if config.type == "simple":
            await run_simple_bot(config, transport, task, context_aggregator)

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await runner.stop_when_done()

        # Run the pipeline
        runner = PipelineRunner()
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
