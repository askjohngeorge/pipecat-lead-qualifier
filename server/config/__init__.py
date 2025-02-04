"""Application configuration package.

This package manages application-wide configuration through:
- Environment variable management
- Type-safe configuration classes
- Validation of required settings
- Default value handling
"""

from .settings import AppConfig

__all__ = ["AppConfig"]
