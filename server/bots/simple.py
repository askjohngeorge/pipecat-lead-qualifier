"""Simple bot implementation using the base bot framework."""

import asyncio

from bots.base_bot import BaseBot
from config.settings import AppConfig
from utils.run_helpers import run_bot
from prompts import SIMPLE_PROMPT


class SimpleBot(BaseBot):
    """Simple bot implementation with single LLM prompt chain."""

    def __init__(self, config: AppConfig):
        # Define the initial system message with conversation instructions
        system_messages = [
            {
                "role": "system",
                "content": f"{SIMPLE_PROMPT}",
            }
        ]
        super().__init__(config, system_messages)

    async def _handle_first_participant(self):
        """Handle actions when the first participant joins."""
        # Queue the context frame for processing
        await self.task.queue_frames(
            [self.context_aggregator.user().get_context_frame()]
        )


async def main():
    """Setup and run the simple voice assistant."""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Simple Bot Server")
    parser.add_argument(
        "-u", "--room-url", type=str, required=True, help="Daily room URL"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=True, help="Authentication token"
    )

    # Optional arguments
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable code reloading")
    parser.add_argument(
        "--bot-type",
        type=str,
        choices=["simple", "flow"],
        default="simple",
        help="Type of bot",
    )

    args = parser.parse_args()

    # Pass the room URL and token to the run_bot function
    await run_bot(SimpleBot, AppConfig, room_url=args.room_url, token=args.token)


if __name__ == "__main__":
    asyncio.run(main())
