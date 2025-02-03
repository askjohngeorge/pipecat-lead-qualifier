# Pipecat Lead Qualifier

A modular voice AI system built with Pipecat AI that combines an embeddable React widget with a flexible bot framework. The system enables natural voice conversations for lead qualification and meeting scheduling through a real-time voice interface that can be integrated into any website.

## Project Components

### Client Widget (client/)
A Next.js-based React widget built with the Pipecat AI SDK (`@pipecat-ai/client-react` and `@pipecat-ai/client-js`). The widget implementation:
- Uses WebRTC via Daily.co transport for real-time audio communication
- Provides a fixed-position, floating UI component that can be embedded in any webpage
- Implements singleton pattern for RTVI client management with environment-based configuration (`client/lib/rtviClient.ts`)
- Manages connection lifecycle with error handling and state management (`client/components/PipecatWidget.tsx`)
- Uses React context for client state distribution (`client/providers/PipecatProvider.tsx`)
- Includes built-in audio playback handling via `RTVIClientAudio`
- Styled with Tailwind CSS using utility-first approach

### Bot Framework (server/)
A FastAPI-based Python framework built on Pipecat AI that provides a robust foundation for building voice-enabled bots. The framework consists of:

#### Core Framework (`server/utils/bot_framework.py`)
- Abstract `BaseBot` class defining the standard bot interface
- Event-driven architecture for real-time voice interactions
- Modular service registry for STT, TTS, and LLM services
- Pipeline-based audio processing with configurable processors
- Standardized lifecycle management for setup, transport, and cleanup

#### Server Implementation (`server/server.py`)
- FastAPI server managing bot instances and WebRTC rooms
- Process-based bot management with automatic cleanup
- Endpoints for both direct browser access and RTVI client connections
- Daily.co room creation and token management
- Configurable bot type selection (simple/flow)
- Background task management for resource cleanup

#### Bot Implementations
1. Simple Lead Qualification Bot (`server/bots/simple.py`):
   - Structured conversation flow for lead qualification
   - Configurable system prompts for bot identity and style
   - Task-driven dialogue management including:
     - Rapport building and contact information collection
     - Use case identification and requirement gathering
     - Project timeline and budget assessment
     - Meeting scheduling and follow-up

2. Flow-based Scheduling Bot (`server/bots/flow.py`):
   - State machine architecture for complex conversation flows
   - Cal.com integration for automated scheduling
   - Structured conversation nodes:
     - Rapport building and initial contact
     - Availability checking with fallback options
     - Time slot presentation and selection
     - Booking confirmation and follow-up
   - Error handling with graceful fallbacks

## Project Structure

```
pipecat-lead-qualifier/
├── client/          # Next.js web application with embeddable widget
│   ├── components/  # React components including PipecatWidget
│   ├── lib/        # Client utilities and RTVI configuration
│   ├── providers/  # React context providers
│   └── app/        # Next.js application routes and layout
├── server/          # Python-based Pipecat AI server and bot framework
│   ├── bots/       # Bot implementations (simple.py, flow.py)
│   ├── utils/      # Framework utilities and core components
│   └── server.py   # FastAPI server implementation
└── docs/           # Project documentation
```

## Features

- Real-time voice conversations using WebRTC via Daily.co
- Event-driven bot framework with modular architecture
- Two bot implementations:
  - Simple lead qualification bot with structured conversation flow
  - Advanced flow-based bot with Cal.com scheduling integration
- Process-based bot management with automatic cleanup
- FastAPI server with async support and background tasks
- Configurable conversation flows and prompts
- Error handling with graceful fallbacks

## Prerequisites

- Node.js 18+ and pnpm for client development
- Python 3.8+ for server development
- Required API keys:
  - Deepgram API key for speech-to-text
  - OpenAI API key for conversation logic
  - Daily.co API key for WebRTC
  - Cal.com API key (optional, for scheduling features)

## Getting Started

### Client Setup

1. Navigate to the client directory:
```bash
cd client
```

2. Install dependencies:
```bash
pnpm install
```

3. Configure environment variables:
Create a `.env.local` file with your API keys and configuration.

4. Start the development server:
```bash
pnpm dev
```

### Server Setup

1. Initialize submodules (if you haven't already):
```bash
git submodule update --init --recursive
```

2. Navigate to the server directory:
```bash
cd server
```

3. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -e "../external/pipecat[daily,openai,deepgram,silero,cartesia,google]"
pip install -e "../external/pipecat-flows"
```

5. Set up environment variables:
Create a `.env` file in the server directory with:
```
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
DAILY_API_KEY=your_daily_api_key
DAILY_SAMPLE_ROOM_URL=your_daily_room_url
```

Note: Ensure you are in the server directory when running these commands. If you need to update the external dependencies, run `git submodule update --remote`.

## Documentation

Detailed documentation is available in the `docs/` directory:
- Flow-based bot implementation guide
- API documentation
- Configuration guides

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
