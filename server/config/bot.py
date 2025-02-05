"""Bot configuration management module."""

import os
from typing import TypedDict, Literal, NotRequired
from dotenv import load_dotenv
from pipecat.services.openai import BaseOpenAILLMService


class DailyConfig(TypedDict):
    api_key: str
    api_url: str
    room_url: NotRequired[str]


BotType = Literal["simple", "flow"]


class BotConfig:
    def __init__(self):
        load_dotenv()

        # Validate required vars
        required = {
            "DAILY_API_KEY": os.getenv("DAILY_API_KEY"),
            "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        self.daily: DailyConfig = {
            "api_key": required["DAILY_API_KEY"],
            "api_url": os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        }

        # Bot configuration
        self._bot_type: BotType = os.getenv("BOT_TYPE", "flow")
        if self._bot_type not in ("simple", "flow"):
            self._bot_type = "flow"  # Default to flow bot if invalid value

    def _is_truthy(self, value: str) -> bool:
        return value.lower() in (
            "true",
            "1",
            "t",
            "yes",
            "y",
            "on",
            "enable",
            "enabled",
        )

    @property
    def bot_name(self) -> str:
        return os.getenv("BOT_NAME", "AskJohnGeorge Lead Qualifier")

    @bot_name.setter
    def bot_name(self, value: str):
        os.environ["BOT_NAME"] = value

    @property
    def tts_provider(self) -> str:
        return os.getenv("TTS_PROVIDER", "deepgram").lower()

    @tts_provider.setter
    def tts_provider(self, value: str):
        value = value.lower()
        if value not in ("deepgram", "cartesia", "elevenlabs"):
            raise ValueError(f"Invalid TTS provider: {value}")

        os.environ["TTS_PROVIDER"] = value

    @property
    def deepgram_api_key(self) -> str:
        return os.getenv("DEEPGRAM_API_KEY")

    @property
    def deepgram_voice(self) -> str:
        return os.getenv("DEEPGRAM_VOICE", "aura-athena-en")

    @deepgram_voice.setter
    def deepgram_voice(self, value: str):
        os.environ["DEEPGRAM_VOICE"] = value

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY")

    @property
    def cartesia_api_key(self) -> str:
        return os.getenv("CARTESIA_API_KEY")

    @property
    def cartesia_voice(self) -> str:
        return os.getenv("CARTESIA_VOICE", "79a125e8-cd45-4c13-8a67-188112f4dd22")

    @cartesia_voice.setter
    def cartesia_voice(self, value: str):
        os.environ["CARTESIA_VOICE"] = value

    @property
    def elevenlabs_api_key(self) -> str:
        return os.getenv("ELEVENLABS_API_KEY")

    @property
    def elevenlabs_voice_id(self) -> str:
        return os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

    @elevenlabs_voice_id.setter
    def elevenlabs_voice_id(self, value: str):
        os.environ["ELEVENLABS_VOICE_ID"] = value

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    @openai_model.setter
    def openai_model(self, value: str):
        os.environ["OPENAI_MODEL"] = value

    @property
    def openai_params(self) -> BaseOpenAILLMService.InputParams:
        temperature = os.getenv("OPENAI_TEMPERATURE", 0.2)
        return BaseOpenAILLMService.InputParams(temperature=temperature)

    @openai_params.setter
    def openai_params(self, value: BaseOpenAILLMService.InputParams):
        os.environ["OPENAI_TEMPERATURE"] = str(value.temperature)

    @property
    def bot_type(self) -> BotType:
        return self._bot_type

    @bot_type.setter
    def bot_type(self, value: BotType):
        self._bot_type = value
        os.environ["BOT_TYPE"] = value

    @property
    def enable_stt_mute_filter(self) -> bool:
        return self._is_truthy(os.getenv("ENABLE_STT_MUTE_FILTER", "false"))

    @enable_stt_mute_filter.setter
    def enable_stt_mute_filter(self, value: bool):
        os.environ["ENABLE_STT_MUTE_FILTER"] = str(value)
