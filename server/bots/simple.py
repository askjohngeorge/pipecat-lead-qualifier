"""Simple bot implementation using the base bot framework."""

from bots.base_bot import BaseBot
from config.bot import BotConfig
from prompts import get_simple_prompt
from loguru import logger


class SimpleBot(BaseBot):
    """Simple bot implementation with single LLM prompt chain."""

    def __init__(self, config: BotConfig):
        # Define the initial system message with conversation instructions
        system_messages = get_simple_prompt()["task_messages"]
        logger.info(f"Initialising SimpleBot with system messages: {system_messages}")
        super().__init__(config, system_messages)

    async def _handle_first_participant(self):
        """Handle actions when the first participant joins."""
        # Queue the context frame for processing
        await self.task.queue_frames([self.context_aggregator.user().get_context_frame()])
