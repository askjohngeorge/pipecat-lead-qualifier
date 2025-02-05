import argparse
import asyncio
import os
from typing import Type

from config.settings import AppConfig


async def run_bot(
    bot_class: Type, config: AppConfig, room_url: str, token: str
) -> None:
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
    """Parse command-line arguments, override configuration if needed, and start the bot.

    The --bot-type argument (if provided) will override the BOT_TYPE setting in the configuration.
    """
    parser = argparse.ArgumentParser(description="Unified Bot Runner")
    parser.add_argument(
        "-u", "--room-url", type=str, required=True, help="Daily room URL"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Authentication token"
    )
    parser.add_argument(
        "--bot-type",
        type=str,
        choices=["simple", "flow"],
        help="Type of bot (overrides BOT_TYPE in configuration)",
    )
    args = parser.parse_args()

    # Instantiate the configuration.
    config = AppConfig()

    # Override the bot type if provided in command-line arguments.
    if args.bot_type:
        config.bot_type = args.bot_type

    # Determine the bot class to use based on the configuration.
    if config.bot_type == "flow":
        from bots.flow import FlowBot

        bot_class = FlowBot
    else:
        from bots.simple import SimpleBot

        bot_class = SimpleBot

    asyncio.run(run_bot(bot_class, config, room_url=args.room_url, token=args.token))


if __name__ == "__main__":
    cli()
