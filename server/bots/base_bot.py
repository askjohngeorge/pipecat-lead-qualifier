"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.google import GoogleLLMService
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.filters.stt_mute_filter import (
    STTMuteFilter,
    STTMuteConfig,
    STTMuteStrategy,
)
from pipecat.services.rime import RimeHttpTTSService
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer

from loguru import logger


class BaseBot(ABC):
    """Abstract base class for bot implementations."""

    def __init__(self, config, system_messages: Optional[List[Dict[str, str]]] = None):
        """Initialize bot with core services and pipeline components.

        Args:
            config: Application configuration.
            system_messages: Optional initial system messages for the LLM context.
        """
        self.config = config

        # Initialize STT service
        self.stt = DeepgramSTTService(api_key=config.deepgram_api_key)

        # Initialize TTS service
        match config.tts_provider:
            case "elevenlabs":
                if not config.elevenlabs_api_key:
                    raise ValueError("ElevenLabs API key is required for ElevenLabs TTS")

                self.tts = ElevenLabsTTSService(
                    api_key=config.elevenlabs_api_key,
                    voice_id=config.elevenlabs_voice_id,
                )
            case "cartesia":
                if not config.cartesia_api_key:
                    raise ValueError("Cartesia API key is required for Cartesia TTS")

                self.tts = CartesiaTTSService(
                    api_key=config.cartesia_api_key, voice_id=config.cartesia_voice
                )
            case "deepgram":
                if not config.deepgram_api_key:
                    raise ValueError("Deepgram API key is required for Deepgram TTS")

                self.tts = DeepgramTTSService(
                    api_key=config.deepgram_api_key, voice=config.deepgram_voice
                )
            case "rime":
                if not config.rime_api_key:
                    raise ValueError("Rime API key is required for Rime TTS")

                self.tts = RimeHttpTTSService(
                    api_key=config.rime_api_key,
                    voice_id=config.rime_voice_id,
                    params=RimeHttpTTSService.InputParams(
                        reduce_latency=config.rime_reduce_latency,
                        speed_alpha=config.rime_speed_alpha,
                    ),
                )
            case _:
                raise ValueError(f"Invalid TTS provider: {config.tts_provider}")

        # Initialize LLM service
        match config.llm_provider:
            case "google":
                if not config.google_api_key:
                    raise ValueError("Google API key is required for Google LLM")

                self.llm = GoogleLLMService(
                    api_key=config.google_api_key,
                    model=config.google_model,
                    params=config.google_params,
                )
            case "openai":
                if not config.openai_api_key:
                    raise ValueError("OpenAI API key is required for OpenAI LLM")

                self.llm = OpenAILLMService(
                    api_key=config.openai_api_key,
                    model=config.openai_model,
                    params=config.openai_params,
                )
            case _:
                raise ValueError(f"Invalid LLM provider: {config.llm_provider}")

        # Initialize context
        self.context = OpenAILLMContext(system_messages)
        self.context_aggregator = self.llm.create_context_aggregator(self.context)

        # Initialize mute filter
        self.stt_mute_filter = (
            STTMuteFilter(
                stt_service=self.stt,
                config=STTMuteConfig(
                    strategies={
                        STTMuteStrategy.FIRST_SPEECH,
                        STTMuteStrategy.FUNCTION_CALL,
                    }
                ),
            )
            if config.enable_stt_mute_filter
            else None
        )

        logger.debug(f"Initialised bot with config: {config}")

        # Initialize transport params
        self.transport_params = DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )

        # Initialize RTVI with default config
        self.rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        # These will be set up when needed
        self.transport: Optional[DailyTransport] = None
        self.task: Optional[PipelineTask] = None
        self.runner: Optional[PipelineRunner] = None

    async def setup_transport(self, url: str, token: str):
        """Set up the transport with the given URL and token."""
        self.transport = DailyTransport(url, token, self.config.bot_name, self.transport_params)

        # Set up basic event handlers
        @self.transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            if self.task:
                await self.task.cancel()

        @self.transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            await self._handle_first_participant()

    def create_pipeline(self):
        """Create the processing pipeline."""
        if not self.transport:
            raise RuntimeError("Transport must be set up before creating pipeline")

        # Build the pipeline using a simple, flat processor list
        pipeline = Pipeline(
            [
                processor
                for processor in [
                    self.rtvi,  # RTVI processor
                    self.transport.input(),  # Transport for user input
                    self.stt_mute_filter,  # STT mute filter
                    self.stt,  # STT service
                    self.context_aggregator.user(),  # User side context aggregation
                    self.llm,  # LLM processor
                    self.tts,  # TTS service
                    self.transport.output(),  # Transport for delivering output
                    self.context_aggregator.assistant(),  # Assistant side context aggregation
                ]
                if processor is not None  # Remove processors disabled via config
            ]
        )

        self.task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )
        self.runner = PipelineRunner()

    async def start(self):
        """Start the bot's main task."""
        if not self.runner or not self.task:
            raise RuntimeError("Bot not properly initialized. Call create_pipeline first.")
        await self.runner.run(self.task)

    async def cleanup(self):
        """Clean up resources."""
        if self.runner:
            await self.runner.stop_when_done()
        if self.transport:
            await self.transport.close()

    @abstractmethod
    async def _handle_first_participant(self):
        """Override in subclass to handle the first participant joining."""
        pass
