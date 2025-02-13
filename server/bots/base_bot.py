"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.parallel_pipeline import ParallelPipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat.processors.filters.function_filter import FunctionFilter
from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.google import GoogleLLMService
from pipecat.services.openai import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import (
    OpenAILLMContext,
    OpenAILLMContextFrame,
)
from pipecat.processors.filters.stt_mute_filter import (
    STTMuteFilter,
    STTMuteConfig,
    STTMuteStrategy,
)
from pipecat.services.rime import RimeHttpTTSService
from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.sync.event_notifier import EventNotifier
from pipecat.processors.user_idle_processor import UserIdleProcessor
from pipecat.frames.frames import (
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    TranscriptionFrame,
    LLMMessagesFrame,
    StartInterruptionFrame,
    StopInterruptionFrame,
    FunctionCallInProgressFrame,
    FunctionCallResultFrame,
)
from deepgram import LiveOptions

from loguru import logger
import time

from .smart_endpointing import (
    CLASSIFIER_SYSTEM_INSTRUCTION,
    CompletenessCheck,
    OutputGate,
    StatementJudgeContextFilter,
)


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
        self.stt = DeepgramSTTService(
            api_key=config.deepgram_api_key, live_options=LiveOptions(model="nova-3-general")
        )

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

        # Initialize LLM services
        match config.llm_provider:
            case "google":
                if not config.google_api_key:
                    raise ValueError("Google API key is required for Google LLM")

                # Main conversation LLM
                system_instruction = (
                    system_messages[0]["content"]
                    if system_messages
                    else "You are a voice assistant"
                )
                self.conversation_llm = GoogleLLMService(
                    api_key=config.google_api_key,
                    model=config.google_model,
                    params=config.google_params,
                    system_instruction=system_instruction,
                )
                self.llm = self.conversation_llm

                # Statement classifier LLM for endpoint detection
                self.statement_llm = GoogleLLMService(
                    name="StatementJudger",
                    api_key=config.google_api_key,
                    model=config.classifier_model,
                    temperature=0.0,
                    system_instruction=CLASSIFIER_SYSTEM_INSTRUCTION,
                )

            case "openai":
                if not config.openai_api_key:
                    raise ValueError("OpenAI API key is required for OpenAI LLM")

                self.conversation_llm = OpenAILLMService(
                    api_key=config.openai_api_key,
                    model=config.openai_model,
                    params=config.openai_params,
                )

                # Note: Smart endpointing currently only supports Google LLM
                raise NotImplementedError(
                    "Smart endpointing is currently only supported with Google LLM"
                )

            case _:
                raise ValueError(f"Invalid LLM provider: {config.llm_provider}")

        # Initialize context
        self.context = OpenAILLMContext(messages=system_messages)
        self.context_aggregator = self.conversation_llm.create_context_aggregator(self.context)

        # Initialize mute filter
        self.stt_mute_filter = (
            STTMuteFilter(
                stt_service=self.stt,
                config=STTMuteConfig(
                    strategies={
                        STTMuteStrategy.MUTE_UNTIL_FIRST_BOT_COMPLETE,
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

        # Initialize smart endpointing components
        self.notifier = EventNotifier()
        self.statement_judge_context_filter = StatementJudgeContextFilter(notifier=self.notifier)
        self.completeness_check = CompletenessCheck(notifier=self.notifier)
        self.output_gate = OutputGate(notifier=self.notifier, start_open=True)

        async def user_idle_notifier(frame):
            await self.notifier.notify()

        self.user_idle = UserIdleProcessor(callback=user_idle_notifier, timeout=5.0)

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

        @self.transport.event_handler("on_app_message")
        async def on_app_message(transport, message, sender):
            if "message" not in message:
                return

            await self.task.queue_frames(
                [
                    UserStartedSpeakingFrame(),
                    TranscriptionFrame(
                        user_id=sender, timestamp=time.time(), text=message["message"]
                    ),
                    UserStoppedSpeakingFrame(),
                ]
            )

    def create_pipeline(self):
        """Create the processing pipeline."""
        if not self.transport:
            raise RuntimeError("Transport must be set up before creating pipeline")

        async def block_user_stopped_speaking(frame):
            return not isinstance(frame, UserStoppedSpeakingFrame)

        async def pass_only_llm_trigger_frames(frame):
            return (
                isinstance(frame, OpenAILLMContextFrame)
                or isinstance(frame, LLMMessagesFrame)
                or isinstance(frame, StartInterruptionFrame)
                or isinstance(frame, StopInterruptionFrame)
                or isinstance(frame, FunctionCallInProgressFrame)
                or isinstance(frame, FunctionCallResultFrame)
            )

        # Define an async filter that always discards frames.
        async def discard_all(frame):
            return False

        # Build pipeline with Deepgram STT at the beginning
        pipeline = Pipeline(
            [
                processor
                for processor in [
                    self.rtvi,
                    self.transport.input(),
                    self.stt_mute_filter,
                    self.stt,  # Deepgram transcribes incoming audio
                    self.context_aggregator.user(),
                    ParallelPipeline(
                        [
                            # Branch 1: Pass everything except UserStoppedSpeakingFrame
                            FunctionFilter(filter=block_user_stopped_speaking),
                        ],
                        [
                            # Branch 2: Endpoint detection branch using Gemini for completeness
                            self.statement_judge_context_filter,
                            self.statement_llm,
                            self.completeness_check,
                            # Use an async filter to discard branch 2's output.
                            FunctionFilter(filter=discard_all),
                        ],
                        [
                            # Branch 3: Conversation branch using Gemini for dialogue
                            FunctionFilter(filter=pass_only_llm_trigger_frames),
                            self.conversation_llm,
                            self.output_gate,
                        ],
                    ),
                    self.tts,
                    self.user_idle,
                    self.transport.output(),
                    self.context_aggregator.assistant(),
                ]
                if processor is not None
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
