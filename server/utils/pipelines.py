from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext


class PipelineBuilder:
    def __init__(self, transport, stt, tts, llm, context=None):
        self._transport = transport
        self._stt = stt
        self._tts = tts
        self._llm = llm
        self._processors = []
        self._context = context or OpenAILLMContext()
        self._context_aggregator = self._llm.create_context_aggregator(self._context)

    def add_rtvi(self, rtvi_config):
        self._processors.append(rtvi_config)
        return self

    def build(self):
        core_processors = [
            self._transport.input(),
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
