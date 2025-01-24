from pipecat.transports.services.daily import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from .config import AppConfig


class TransportFactory:
    def __init__(self, config: AppConfig):
        self._default_params = DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        )

    def create_flow_assistant_transport(self, room_url: str, token: str):
        return DailyTransport(
            room_url, token, "Lead Qualification Bot", self._default_params
        )

    def create_simple_assistant_transport(self, room_url: str, token: str):
        return DailyTransport(room_url, token, "Voice Assistant", self._default_params)
