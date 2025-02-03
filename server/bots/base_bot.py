"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.filters.stt_mute_filter import (
    STTMuteFilter,
    STTMuteConfig,
    STTMuteStrategy,
)
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer


class BaseBot(ABC):
    """Abstract base class for bot implementations."""

    def __init__(self, config, system_messages: Optional[List[Dict[str, str]]] = None):
        """Initialize bot with core services and pipeline components.

        Args:
            config: Application configuration.
            system_messages: Optional initial system messages for the LLM context.
        """
        self.config = config

        # Initialize services
        self.stt = DeepgramSTTService(api_key=config.deepgram_api_key)
        self.tts = DeepgramTTSService(
            api_key=config.deepgram_api_key, voice=config.deepgram_voice
        )
        self.llm = OpenAILLMService(
            api_key=config.openai_api_key,
            model=config.openai_model,
            params=config.openai_params,
        )

        # Initialize mute filter
        self.stt_mute_config = STTMuteConfig(
            strategies={STTMuteStrategy.FIRST_SPEECH, STTMuteStrategy.FUNCTION_CALL}
        )
        self.stt_mute_filter = STTMuteFilter(
            stt_service=self.stt, config=self.stt_mute_config
        )

        # Initialize context
        self.context = OpenAILLMContext(system_messages)
        self.context_aggregator = self.llm.create_context_aggregator(self.context)

        # Initialize transport params
        self.transport_params = DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )

        # These will be set up when needed
        self.transport: Optional[DailyTransport] = None
        self.task: Optional[PipelineTask] = None
        self.runner: Optional[PipelineRunner] = None

    async def setup_transport(self, url: str, token: str):
        """Set up the transport with the given URL and token."""
        self.transport = DailyTransport(
            url, token, "Lead Qualification Bot", self.transport_params
        )

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
                self.transport.input(),  # Transport for user input
                self.stt_mute_filter,  # STT mute filter
                self.stt,  # STT service
                self.context_aggregator.user(),  # User side context aggregation
                self.llm,  # LLM processor
                self.tts,  # TTS service
                self.transport.output(),  # Transport for delivering output
                self.context_aggregator.assistant(),  # Assistant side context aggregation
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
            raise RuntimeError(
                "Bot not properly initialized. Call create_pipeline first."
            )
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
