"""Service Registry for managing shared services."""

from typing import Optional
from dataclasses import dataclass

from pipecat.services.deepgram import DeepgramSTTService, DeepgramTTSService
from pipecat.services.openai import OpenAILLMService


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
        self.stt = DeepgramSTTService(api_key=config.deepgram_api_key)
        self.tts = DeepgramTTSService(api_key=config.deepgram_api_key)
        self.llm = OpenAILLMService(api_key=config.openai_api_key)
