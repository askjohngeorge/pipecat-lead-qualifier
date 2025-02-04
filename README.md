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
- **Directory:** `server/`

#### Key Files
- **`server/server.py`**  
  The main FastAPI server handling endpoints for room creation and bot management.
- **`server/Dockerfile`**  
  Docker configuration for containerizing the server.
- **`server/requirements.txt`**  
  Defines the Python dependencies.
- **`server/bots/`**  
  Contains the bot implementations (`base_bot.py`, `flow.py`, `simple.py`).
- **`server/utils/`**  
  Includes various configuration and integration utilities.

### Client

#### Directory Structure
- **Directory:** `client/`

#### Overview
- Developed with Next.js using TypeScript with strict type checking.
- Follows Next.js conventions: routes under `/app` (or `/pages`), shared components in `/components`, and styles in `/styles` or via CSS Modules.
- Managed with pnpm for dependency handling.

## Setup and Installation

### Environment Setup

Create a `.env` file with the required environment variables:
```bash
cat << 'EOF' > .env
DAILY_API_KEY=your_daily_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key

# Optional variables (override defaults as needed)
DAILY_API_URL=https://api.daily.co/v1
TTS_PROVIDER=cartesia              # Optional: indicates a preference, but CARTESIA_API_KEY is what drives the Cartesia integration.
DEEPGRAM_VOICE=aura-athena-en
CARTESIA_API_KEY=your_cartesia_api_key  # Provide only if you want to use Cartesia TTS.
CARTESIA_VOICE=your_cartesia_voice_identifier
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.2
BOT_TYPE=flow                      # or "simple"
EOF
```

Ensure that the `.env` file is excluded from version control:
```bash
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
```

### Advanced Configuration Options

In addition to the required environment variables (`DAILY_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, and `OPENAI_API_KEY`), you can customize the behavior of the application by setting the following optional environment variables in your `.env` file:

- **DAILY_API_URL**  
  - **Default:** `https://api.daily.co/v1`  
  - **Usage:** Sets the base URL for the Daily API. This URL is used when initializing the Daily transport in the bot.
  
- **TTS_PROVIDER**  
  - **Default:** `deepgram`  
  - **Usage:** Determines which Text-to-Speech service your bot will use.  
    - If set to `cartesia`, the application uses the `CartesiaTTSService` and relies on the **CARTESIA_API_KEY** and **CARTESIA_VOICE** values.  
    - Otherwise, it uses `DeepgramTTSService` along with **DEEPGRAM_API_KEY** and **DEEPGRAM_VOICE**.

- **DEEPGRAM_VOICE**  
  - **Default:** `aura-athena-en`  
  - **Usage:** Specifies the voice identifier for the Deepgram TTS service when **TTS_PROVIDER** is not set to `cartesia`.

- **CARTESIA_VOICE**  
  - **Default:** `79a125e8-cd45-4c13-8a67-188112f4dd22`  
  - **Usage:** Specifies the voice identifier for the Cartesia TTS service. This is used only if **TTS_PROVIDER** is set to `cartesia`.

- **OPENAI_MODEL**  
  - **Default:** `gpt-4o`  
  - **Usage:** Determines which OpenAI model to use when initializing the LLM service in the bot.

- **OPENAI_TEMPERATURE**  
  - **Default:** `0.2`  
  - **Usage:** Controls the temperature (randomness) of the OpenAI language model. The value is passed as part of the `InputParams` to the LLM service.

- **BOT_TYPE**  
  - **Default:** `simple`  
  - **Valid Values:** `simple` or `flow`  
  - **Usage:** Specifies which bot variant to launch. This setting is checked at startup and used to determine the corresponding bot implementation within the `server/bots/` package.

These optional variables are processed by the `AppConfig` class in `server/utils/config.py`. In the `server/bots/base_bot.py` module, the configuration is used as follows:

- **STT & TTS Initialization:**  
  The bot initializes Deepgram’s STT service using **DEEPGRAM_API_KEY**. Depending on **TTS_PROVIDER**, it either initializes the Deepgram TTS service (using **DEEPGRAM_VOICE**) or the Cartesia TTS service (using **CARTESIA_API_KEY** and **CARTESIA_VOICE**).

- **LLM Setup:**  
  The bot sets up the OpenAI LLM service with **OPENAI_API_KEY**, **OPENAI_MODEL**, and additional parameters (such as **OPENAI_TEMPERATURE** bundled into the `InputParams`). This is used to drive conversation logic.

- **Bot Behavior:**  
  The **BOT_TYPE** variable determines whether a “simple” or “flow” bot implementation is executed; this affects the orchestration and logic sequence within the bot’s processing pipeline.

By adjusting these variables in your `.env` file, you can fine-tune service integrations and bot behavior without modifying the application code.

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
pip install -e "../external/pipecat[daily,openai,deepgram,cartesia,silero]"
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
python server/server.py --bot-type flow  # Use "simple" instead of "flow" for the simple bot variant
```

#### Docker Container
Build and run the server in a Docker container. The Dockerfile installs the `pipecat-ai` package with the `[daily,openai,deepgram,silero]` extras and the `pipecat-ai-flows` package from PyPI.
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

## Contributing

Please adhere to the project conventions:
- Write clear, modular functions with single purposes.
- Follow SOLID principles.
- For client-side development, adhere to Next.js and TypeScript guidelines.
- For server-side development, follow FastAPI and Pipecat conventions.

## License

[MIT License](LICENSE.md)

## Contact

For any questions or issues, please contact [your-email@example.com](mailto:your-email@example.com).
