from aiohttp import ClientSession


async def run_bot(bot_class, config_class, room_url: str, token: str):
    """Universal bot runner handling bot lifecycle.

    Args:
        bot_class: The bot class to instantiate (e.g. FlowBot)
        config_class: The configuration class to use (e.g. AppConfig)
        room_url: The Daily room URL
        token: The Daily room token
    """
    # Create bot instance (this initializes all core services)
    config = config_class()
    bot = bot_class(config)

    # Set up transport and pipeline
    async with ClientSession() as session:
        await bot.setup_transport(room_url, token)
        bot.create_pipeline()
        await bot.start()
