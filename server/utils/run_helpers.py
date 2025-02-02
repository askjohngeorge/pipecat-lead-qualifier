import argparse
from aiohttp import ClientSession


async def run_bot(bot_class, config_class):
    """Universal bot runner handling CLI args and lifecycle.

    Args:
        bot_class: The bot class to instantiate (e.g. FlowBot)
        config_class: The configuration class to use (e.g. AppConfig)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    args = parser.parse_args()

    # Create bot instance (this initializes all core services)
    config = config_class()
    bot = bot_class(config)

    # Set up transport and pipeline
    async with ClientSession() as session:
        await bot.setup_transport(args.url, args.token)
        bot.create_pipeline()
        await bot.start()
