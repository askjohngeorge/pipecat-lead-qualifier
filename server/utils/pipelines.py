from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.filters.stt_mute_filter import (
    STTMuteFilter,
    STTMuteConfig,
    STTMuteStrategy,
)


class PipelineBuilder:
    def __init__(self, transport, stt, tts, llm, context=None, stt_mute_config=None):
        self._transport = transport
        self._stt = stt
        self._tts = tts
        self._llm = llm
        self._processors = []
        self._context = context or OpenAILLMContext()
        self._context_aggregator = self._llm.create_context_aggregator(self._context)
        self._stt_mute_config = stt_mute_config or STTMuteConfig(
            strategies={STTMuteStrategy.FIRST_SPEECH, STTMuteStrategy.FUNCTION_CALL}
        )

    def add_rtvi(self, rtvi_config):
        self._processors.append(rtvi_config)
        return self

    def build(self):
        stt_mute_processor = STTMuteFilter(
            stt_service=self._stt, config=self._stt_mute_config
        )

        core_processors = [
            self._transport.input(),
            stt_mute_processor,
            self._stt,
            self._context_aggregator.user(),
            self._llm,
            self._tts,
            self._transport.output(),
            self._context_aggregator.assistant(),
        ]

        return Pipeline(self._processors + core_processors)

    @property
    def context(self):
        return self._context

    @property
    def context_aggregator(self):
        return self._context_aggregator
