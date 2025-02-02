"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from typing import Optional

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer


class BaseBot(ABC):
    """Abstract base class for bot implementations."""

    def __init__(self, config):
        self.config = config
        # Services
        self.stt: Optional[DeepgramSTTService] = None
        self.tts: Optional[DeepgramTTSService] = None
        self.llm: Optional[OpenAILLMService] = None
        # Transport and context
        self.transport: Optional[DailyTransport] = None
        self.context: Optional[OpenAILLMContext] = None
        self.context_aggregator = None
        # Pipeline components
        self.task: Optional[PipelineTask] = None
        self.runner: Optional[PipelineRunner] = None

    async def setup_services(self):
        """Initialize required services with direct instantiation."""
        # Initialize STT and TTS services
        self.stt = DeepgramSTTService(api_key=self.config.deepgram_api_key)
        self.tts = DeepgramTTSService(
            api_key=self.config.deepgram_api_key, voice=self.config.deepgram_voice
        )

        # Initialize LLM service
        self.llm = OpenAILLMService(
            api_key=self.config.openai_api_key,
            model=self.config.openai_model,
            params=self.config.openai_params,
        )

        # Initialize conversation context
        self.context = OpenAILLMContext()
        self.context_aggregator = self.llm.create_context_aggregator(self.context)

        # Call implementation-specific service setup
        await self._setup_services_impl()

    async def setup_transport(self, url: str, token: str):
        """Set up the transport using DailyTransport directly."""
        # Create transport with default parameters
        default_params = DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )

        # Create transport instance
        self.transport = await self._create_transport(url, token)

        # Set up basic event handlers
        if hasattr(self.transport, "event_handler"):

            @self.transport.event_handler("on_participant_left")
            async def on_participant_left(transport, participant, reason):
                if self.runner:
                    await self.runner.stop_when_done()

            @self.transport.event_handler("on_first_participant_joined")
            async def on_first_participant_joined(transport, participant):
                await transport.capture_participant_transcription(participant["id"])
                await self._handle_first_participant()

        # Call implementation-specific transport setup
        await self._setup_transport_impl()

    def create_pipeline(self):
        """Create the processing pipeline inline similar to the interruptible example."""
        # Build the pipeline using a simple, flat processor list
        pipeline = Pipeline(
            [
                self.transport.input(),  # Transport for user input
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

        # Call implementation-specific pipeline setup
        self._create_pipeline_impl()

    async def start(self):
        """Start the bot's main task."""
        if not self.runner or not self.task:
            raise RuntimeError(
                "Bot not properly initialized. Ensure setup methods are called first."
            )
        await self.runner.run(self.task)

    async def cleanup(self):
        """Clean up resources."""
        if self.runner:
            await self.runner.stop_when_done()
        if self.transport:
            await self.transport.close()

    @abstractmethod
    async def _setup_services_impl(self):
        """Override in subclass for additional service setup."""
        pass

    @abstractmethod
    async def _create_transport(self, url: str, token: str):
        """Override in subclass if custom transport creation is needed."""
        pass

    @abstractmethod
    async def _handle_first_participant(self):
        """Override in subclass for handling the first participant."""
        pass

    def _create_pipeline_impl(self):
        """Optional pipeline modifications. Subclasses can override as needed."""
        pass

    async def _setup_transport_impl(self):
        """Optional transport-specific setup. Subclasses can override."""
        pass
