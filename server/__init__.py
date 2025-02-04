"""Lead Qualification Voice AI Server.

This package implements a FastAPI server that manages voice AI bots for lead qualification.
The server provides:
- Bot lifecycle management (creation, monitoring, cleanup)
- HTTP endpoints for browser and RTVI client access
- Integration with Daily.co for video/audio communication
- Configurable bot types (simple and flow-based)

The package is organized into several submodules:
- bots/: Bot implementations and base framework
- config/: Application configuration management
- prompts/: LLM system prompts and templates
- services/: External API integrations
- utils/: Common utility functions
"""

__version__ = "0.1.0"
