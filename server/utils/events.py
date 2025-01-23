"""Event framework for handling transport events."""

from typing import Callable, Awaitable, Any
from functools import wraps


class EventFramework:
    """Framework for managing transport events."""

    def __init__(self, transport):
        self.transport = transport

    async def register_default_handlers(
        self, cleanup_callback: Callable[[], Awaitable[None]]
    ):
        """Register default event handlers for the transport.

        Args:
            cleanup_callback: Async function to call during cleanup
        """

        @self.transport.event_handler("on_first_participant_joined")
        async def handle_join(transport, participant):
            await transport.capture_participant_transcription()

        @self.transport.event_handler("on_last_participant_left")
        async def handle_leave(transport):
            if cleanup_callback:
                await cleanup_callback()

        @self.transport.event_handler("on_error")
        async def handle_error(transport, error):
            print(f"Transport error occurred: {error}")
            if cleanup_callback:
                await cleanup_callback()

    def register_custom_handler(
        self, event_name: str, handler: Callable[..., Awaitable[Any]]
    ):
        """Register a custom event handler.

        Args:
            event_name: Name of the event to handle
            handler: Async function to handle the event
        """

        @self.transport.event_handler(event_name)
        @wraps(handler)
        async def wrapped_handler(*args, **kwargs):
            return await handler(*args, **kwargs)
