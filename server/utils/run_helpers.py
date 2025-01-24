import argparse
import asyncio
from aiohttp import ClientSession


async def run_bot(bot_class, config_class):
    """Universal bot runner handling CLI args and lifecycle"""
    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument("-u", "--url", type=str, required=True, help="Daily room URL")
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Daily room token"
    )
    args = parser.parse_args()

    config = config_class()
    bot = bot_class(config)

    async with ClientSession() as session:
        await bot.setup_services()
        await bot.setup_transport(args.url, args.token)
        bot.create_pipeline()
        await bot.start()
