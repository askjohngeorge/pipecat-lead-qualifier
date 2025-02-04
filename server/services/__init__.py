"""External service integrations package.

This package contains modules for interacting with external services and APIs.
Each module provides a typed interface and follows consistent patterns for:
- Configuration management
- Error handling
- Retry mechanisms
- Logging
"""

from .calcom_api import CalComAPI

__all__ = ["CalComAPI"]
