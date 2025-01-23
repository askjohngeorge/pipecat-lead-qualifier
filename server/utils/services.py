"""Service Registry for managing shared services."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ServiceRegistry:
    """Singleton registry for managing shared services across bots."""

    _instance: Optional["ServiceRegistry"] = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._init_services(config)
        return cls._instance

    def _init_services(self, config):
        """Initialize core services with configuration."""
        from pipecat.services import (
            DeepgramSTTService,
            DeepgramTTSService,
            OpenAILLMService,
        )

        self.stt = DeepgramSTTService(config.deepgram_api_key)
        self.tts = DeepgramTTSService(config.deepgram_api_key)
        self.llm = OpenAILLMService(config.openai_api_key)
