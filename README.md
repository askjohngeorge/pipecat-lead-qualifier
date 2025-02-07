# Pipecat Lead Qualifier

Pipecat Lead Qualifier is a modular voice assistant application that uses a FastAPI server to orchestrate bot workflows and a Next.js client for user interactions.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
  - [Server](#server)
  - [Client](#client)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Project Overview

The project qualifies leads by guiding users through a series of conversational steps. It comprises two main components:

1. **Server:** Built with FastAPI, this component manages bot workflows and handles integrations (e.g., Daily rooms, transcription, TTS, and OpenAI services).
2. **Client:** Developed with Next.js and TypeScript, this component serves as the front-facing widget.

## Architecture

### Server

#### Directory Structure
```
server/
├── __init__.py            # Package initialization and version info
├── main.py                # FastAPI server entry point
├── runner.py              # Bot runner CLI and lifecycle management
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
├── bots/                  # Bot implementations
│   ├── __init__.py
│   ├── base_bot.py        # Shared bot framework
│   ├── flow.py            # Flow-based bot implementation
│   └── simple.py          # Simple bot implementation
├── config/                # Configuration management
│   ├── __init__.py
│   ├── bot.py             # Bot-specific settings and env var handling
│   └── server.py          # Server network and runtime configuration
├── prompts/               # LLM system prompts
│   ├── __init__.py        # Package initialization; exposes flow, simple, helpers, and types modules
│   ├── flow.py            # Flow-based prompt definitions for conversation workflows
│   ├── simple.py          # Simple, direct prompt definitions for one-off interactions
│   ├── helpers.py         # Helper functions for prompt generation and manipulation
│   └── types.py           # Type definitions for prompt structures
├── services/              # External API integrations
│   ├── __init__.py
│   └── calcom_api.py      # Cal.com API client
```

#### Key Components

- **`main.py`**  
  The FastAPI server entry point that handles:
  - Room creation and management
  - Bot process lifecycle
  - HTTP endpoints for browser and RTVI access
  - Connection credential management

- **`runner.py`**  
  The bot runner CLI that handles:
  - Bot configuration via CLI arguments
  - Environment variable overrides
  - Bot process initialization
  - Supported CLI arguments:
    ```bash
    -u/--room-url      Daily room URL (required)
    -t/--token         Daily room token (required)
    -b/--bot-type      Bot variant [simple|flow]
    -p/--tts-provider  TTS service [deepgram|cartesia|elevenlabs|rime]
    -m/--openai-model  OpenAI model name
    -T/--temperature   LLM temperature (0.0-2.0)
    -n/--bot-name      Custom bot name
    ```

- **`bots/`**  
  Contains bot implementations with:
  - `base_bot.py`: Shared framework and service initialization
  - `flow.py`: Sophisticated flow-based conversation logic
  - `simple.py`: Basic single-prompt implementation

- **`config/`**  
  Manages application configuration:
  - Environment variable validation
  - Type-safe settings classes
  - Default value handling

- **`prompts/`**  
  Contains the modular LLM system prompts including:
  - `flow.py`: Flow-based prompt definitions for conversational flows
  - `simple.py`: Simple prompt definitions for the single prompt agent
  - `helpers.py`: Functions to assist in prompt generation and maintenance
  - `types.py`: Definitions for prompt structure and types

- **`services/`**  
  External API integrations:
  - Cal.com API for appointment scheduling
  - Additional integrations can be added as needed

- **`utils/`**  
  Common utilities and helper functions:
  - Bot lifecycle management
  - Shared helper functions

### Client

#### Directory Structure
- **Directory:** `client/`

#### Overview
- Developed with Next.js using TypeScript with strict type checking.
- Follows Next.js conventions: routes under `/app` or `/pages`, shared components in `/components`, and styles in `/styles` or via CSS Modules.
- Managed with pnpm for dependency handling.

## Setup and Installation

### Environment Setup

Create a `.env` file with the required environment variables:
```bash
# Required API Keys
DAILY_API_KEY=your_daily_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# LLM Configuration (Google is default)
GOOGLE_API_KEY=your_google_api_key        # Required for Google LLM
GOOGLE_MODEL=gemini-2.0-flash             # Default Google model
GOOGLE_TEMPERATURE=1.0                     # Default Google temperature

# Optional OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key        # Required if using OpenAI
OPENAI_MODEL=gpt-4o                       # Default OpenAI model
OPENAI_TEMPERATURE=0.2                    # Default OpenAI temperature

# TTS Configuration
TTS_PROVIDER=deepgram                     # Options: deepgram, cartesia, elevenlabs, rime
DEEPGRAM_VOICE=aura-athena-en            # Default Deepgram voice
CARTESIA_API_KEY=your_cartesia_api_key   # Required if using Cartesia TTS
CARTESIA_VOICE=your_cartesia_voice_id    # Default: 79a125e8-cd45-4c13-8a67-188112f4dd22
ELEVENLABS_API_KEY=your_elevenlabs_key   # Required if using ElevenLabs TTS
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb # Default ElevenLabs voice
RIME_API_KEY=your_rime_api_key           # Required if using Rime TTS
RIME_VOICE_ID=marissa                    # Default Rime voice

# Bot Configuration
BOT_TYPE=flow                            # Options: flow, simple (default: flow)
BOT_NAME="AskJohnGeorge Lead Qualifier"  # Default bot name
LLM_PROVIDER=google                      # Options: google, openai (default: google)
ENABLE_STT_MUTE_FILTER=false            # Enable STT mute filter (default: false)

# Optional overrides
DAILY_API_URL=https://api.daily.co/v1    # Default Daily API URL
```

Ensure that the `.env` file is excluded from version control:
```bash
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
```

### Advanced Configuration Options

The application supports extensive configuration through environment variables and CLI arguments. Here's a detailed breakdown:

#### LLM Configuration
- **LLM Provider Selection**
  - Default provider is Google (Gemini)
  - Can be switched to OpenAI via `LLM_PROVIDER=openai`
  - Each provider has its own model and temperature settings

- **Google LLM Settings**
  - Model: `GOOGLE_MODEL` (default: gemini-2.0-flash)
  - Temperature: `GOOGLE_TEMPERATURE` (default: 1.0)

- **OpenAI Settings**
  - Model: `OPENAI_MODEL` (default: gpt-4o)
  - Temperature: `OPENAI_TEMPERATURE` (default: 0.2)

#### TTS Configuration
The application supports multiple TTS providers:
- Deepgram (default)
- Cartesia
- ElevenLabs
- Rime

Each provider requires its own API key and has configurable voice settings.

#### Bot Configuration
- Bot Type: `flow` (default) or `simple`
- Custom bot name
- STT mute filter toggle

### CLI Arguments

The bot runner (`runner.py`) supports the following command-line arguments:

```bash
Required arguments:
  -u, --room-url              Daily room URL
  -t, --token                 Authentication token

Bot configuration:
  -b, --bot-type             Type of bot [simple|flow] (default: flow)
  -n, --bot-name             Override BOT_NAME

LLM configuration:
  -l, --llm-provider         LLM service provider [google|openai] (default: google)
  
  # Google-specific options
  -m, --google-model         Override GOOGLE_MODEL
  -T, --google-temperature   Override GOOGLE_TEMPERATURE (default: 1.0)
  
  # OpenAI-specific options
  --openai-model            Override OPENAI_MODEL (default: gpt-4o)
  --openai-temperature      Override OPENAI_TEMPERATURE (default: 0.2)

TTS configuration:
  -p, --tts-provider         TTS service [deepgram|cartesia|elevenlabs|rime] (default: deepgram)
  --deepgram-voice           Override DEEPGRAM_VOICE
  --cartesia-voice           Override CARTESIA_VOICE
  --elevenlabs-voice-id      Override ELEVENLABS_VOICE_ID
  --rime-voice-id            Override RIME_VOICE_ID

Additional options:
  --enable-stt-mute-filter   Enable STT mute filter [true|false] (default: false)
```

### Server Setup

Navigate to the `server` directory, set up a virtual environment, and install the dependencies:
```bash
cd server
python -m venv venv
# Activate the virtual environment:
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
pip install -r requirements.txt
pip install -e "../external/pipecat[daily,google,anthropic,openai,deepgram,cartesia,silero]"
pip install -e "../external/pipecat-flows"
```

### Client Setup

Navigate to the `client` directory and install dependencies using pnpm:
```bash
cd ../client
pnpm install
```

## Running the Application

### Server

#### Local Development
Run the server from the `server` directory:
```bash
python -m main --bot-type flow  # Use "simple" instead of "flow" for the simple bot variant
```

#### Docker Container
Build and run the server in a Docker container:
```bash
docker build -t pipecat-server:latest -f server/Dockerfile .
docker run -p 7860:7860 pipecat-server:latest
```

### Client

#### Development Mode
Run the Next.js client in development mode:
```bash
pnpm dev
```

#### Production Build
To build and start the production version of the client:
```bash
pnpm build
pnpm start
```

## Testing

- **Server:**  
  Follow the testing guidelines provided in the codebase. Tests should use the Arrange-Act-Assert pattern to verify API endpoints and bot functionalities.
  
- **Client:**  
  Execute frontend tests using your preferred test runner (e.g., Jest).

## License

[MIT License](LICENSE.md)

## Contact

For any questions or issues, please contact [john@askjohngeorge.com](mailto:john@askjohngeorge.com).