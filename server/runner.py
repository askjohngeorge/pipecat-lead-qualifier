import argparse
import asyncio
import os
from typing import Type

from config.bot import BotConfig


async def run_bot(bot_class: Type, config: BotConfig, room_url: str, token: str) -> None:
    """Universal bot runner handling bot lifecycle.

    Args:
        bot_class: The bot class to instantiate (e.g. FlowBot or SimpleBot)
        config: The configuration instance to use (with bot_type possibly overridden)
        room_url: The Daily room URL
        token: The Daily room token
    """
    # Instantiate the bot using the provided configuration instance.
    bot = bot_class(config)

    # Set up transport and pipeline.
    await bot.setup_transport(room_url, token)
    bot.create_pipeline()

    # Start the bot.
    await bot.start()


def cli() -> None:
    """Parse command-line arguments, override configuration if needed, and start the bot."""
    parser = argparse.ArgumentParser(description="Unified Bot Runner")

    # Required arguments
    parser.add_argument("-u", "--room-url", type=str, required=True, help="Daily room URL")
    parser.add_argument("-t", "--token", type=str, required=True, help="Authentication token")

    # Bot type selection
    parser.add_argument(
        "-b",
        "--bot-type",
        type=str.lower,
        choices=["simple", "flow"],
        help="Type of bot (overrides BOT_TYPE in configuration)",
    )

    # TTS configuration
    parser.add_argument(
        "-p",
        "--tts-provider",
        type=str.lower,
        choices=["deepgram", "cartesia", "elevenlabs", "rime"],
        help="Override TTS_PROVIDER (default: deepgram)",
    )

    # Voice configuration
    parser.add_argument(
        "--deepgram-voice",
        type=str,
        help="Override DEEPGRAM_VOICE (default: aura-athena-en)",
    )
    parser.add_argument(
        "--cartesia-voice",
        type=str,
        help="Override CARTESIA_VOICE",
    )
    parser.add_argument(
        "--elevenlabs-voice-id",
        type=str,
        help="Override ELEVENLABS_VOICE_ID",
    )

    # OpenAI configuration
    parser.add_argument(
        "-m",
        "--openai-model",
        type=str,
        help="Override OPENAI_MODEL (default: gpt-4o)",
    )
    parser.add_argument(
        "-T",
        "--openai-temperature",
        type=float,
        help="Override OPENAI_TEMPERATURE (default: 0.2)",
    )

    # Bot name configuration
    parser.add_argument(
        "-n",
        "--bot-name",
        type=str,
        help="Override BOT_NAME",
    )

    # STT mute filter configuration
    parser.add_argument(
        "--enable-stt-mute-filter",
        type=lambda x: str(x).lower() in ("true", "1", "t", "yes", "y", "on", "enable", "enabled"),
        help="Override ENABLE_STT_MUTE_FILTER (true/false)",
    )

    args = parser.parse_args()

    # Set environment variables based on CLI arguments
    if args.bot_type:
        os.environ["BOT_TYPE"] = args.bot_type
    if args.tts_provider:
        os.environ["TTS_PROVIDER"] = args.tts_provider.lower()
    if args.deepgram_voice:
        os.environ["DEEPGRAM_VOICE"] = args.deepgram_voice
    if args.cartesia_voice:
        os.environ["CARTESIA_VOICE"] = args.cartesia_voice
    if args.elevenlabs_voice_id:
        os.environ["ELEVENLABS_VOICE_ID"] = args.elevenlabs_voice_id
    if args.openai_model:
        os.environ["OPENAI_MODEL"] = args.openai_model
    if args.openai_temperature is not None:
        os.environ["OPENAI_TEMPERATURE"] = str(args.openai_temperature)
    if args.bot_name:
        os.environ["BOT_NAME"] = args.bot_name
    if args.enable_stt_mute_filter is not None:
        os.environ["ENABLE_STT_MUTE_FILTER"] = str(args.enable_stt_mute_filter).lower()

    # Instantiate the configuration AFTER setting environment variables
    config = BotConfig()

    # Determine the bot class to use based on the configuration
    if config.bot_type == "flow":
        from bots.flow import FlowBot

        bot_class = FlowBot
    else:
        from bots.simple import SimpleBot

        bot_class = SimpleBot

    asyncio.run(run_bot(bot_class, config, room_url=args.room_url, token=args.token))


if __name__ == "__main__":
    cli()
