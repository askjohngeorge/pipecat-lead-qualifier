"""Application configuration package.

This package manages application-wide configuration through:
- Environment variable management
- Type-safe configuration classes
- Validation of required settings
- Default value handling
"""

from .bot import BotConfig
from .server import ServerConfig

__all__ = ["BotConfig", "ServerConfig"]
