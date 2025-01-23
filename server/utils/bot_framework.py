"""Base bot framework for shared functionality."""

from abc import ABC, abstractmethod
from typing import Optional
from .services import ServiceRegistry


class BaseBot(ABC):
    """Abstract base class for bot implementations."""

    def __init__(self, config):
        self.config = config
        self.services = ServiceRegistry(config)
        self.runner = None  # Will be set by concrete implementations
        self.transport = None
        self.task = None

    @abstractmethod
    async def setup_services(self):
        """Initialize required services."""
        pass

    @abstractmethod
    async def setup_transport(self, url: str, token: str):
        """Initialize and configure transport."""
        pass

    @abstractmethod
    def create_pipeline(self):
        """Build the processing pipeline."""
        pass

    async def start(self):
        """Start the bot's main task."""
        if self.runner and self.task:
            await self.runner.run(self.task)
        else:
            raise RuntimeError(
                "Bot not properly initialized. Call setup methods first."
            )

    async def cleanup(self):
        """Clean up resources."""
        if self.runner:
            await self.runner.stop_when_done()
        if self.transport:
            await self.transport.leave()
