"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from .services import ServiceRegistry
from .transports import TransportFactory
from .events import EventFramework
from .pipelines import PipelineBuilder


class BaseBot(ABC):
    """Abstract base class for bot implementations."""

    def __init__(self, config):
        self.config = config
        self.services = ServiceRegistry(config)
        self.runner = None
        self.transport = None
        self.task = None
        self.rtvi = None
        self.context = None
        self.context_aggregator = None
        self.pipeline_builder = None

    async def setup_services(self):
        """Initialize required services with common setup."""
        # Initialize RTVI with default config
        rtvi_config = RTVIConfig(config=[])
        self.rtvi = RTVIProcessor(config=rtvi_config)

        # Set up RTVI ready handler
        @self.rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            await rtvi.set_bot_ready()

        # Allow subclasses to do additional setup
        await self._setup_services_impl()

    @abstractmethod
    async def _setup_services_impl(self):
        """Implementation-specific service setup."""
        pass

    @abstractmethod
    async def _create_transport(self, factory: TransportFactory, url: str, token: str):
        """Implementation-specific transport creation."""
        pass

    @abstractmethod
    async def _handle_first_participant(self):
        """Implementation-specific first participant handling."""
        pass

    async def setup_transport(self, url: str, token: str):
        """Standard transport setup with common event handlers"""
        transport_factory = TransportFactory(self.config)
        self.transport = await self._create_transport(transport_factory, url, token)

        # Set up event handlers
        event_framework = EventFramework(self.transport)
        await event_framework.register_default_handlers(self.cleanup)

        # Common event handlers
        @self.transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            await self.runner.stop_when_done()

        @self.transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await transport.capture_participant_transcription(participant["id"])
            await self._handle_first_participant()

        # Set up RTVI ready handler
        @self.rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            await rtvi.set_bot_ready()

        await self._setup_transport_impl()

    async def _setup_transport_impl(self):
        """Optional implementation-specific transport setup."""
        pass

    def create_pipeline(self):
        """Standard pipeline construction"""
        self.pipeline_builder = PipelineBuilder(
            self.transport,
            self.services.stt,
            self.services.tts,
            self.services.llm,
            context=self.context,
        )
        pipeline = self.pipeline_builder.add_rtvi(self.rtvi).build()

        # Common task configuration
        self.task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                observers=[self.rtvi.observer()],
            ),
        )
        self.runner = PipelineRunner()
        self._create_pipeline_impl()

    def _create_pipeline_impl(self):
        """Optional implementation-specific pipeline setup."""
        pass

    async def start(self):
        """Start the bot's main task."""
        if self.runner and self.task:
            await self.runner.run(self.task)
        else:
            raise RuntimeError(
                "Bot not properly initialized. Call setup methods first."
            )

    async def cleanup(self):
        """Clean up resources."""
        if self.runner:
            await self.runner.stop_when_done()
        if self.transport:
            await self.transport.close()
