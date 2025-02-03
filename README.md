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
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
DAILY_API_KEY=your_daily_api_key
EOF
```

Ensure that the `.env` file is excluded from version control:
```bash
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
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
pip install -e "../external/pipecat[daily,openai,deepgram,silero]"
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
