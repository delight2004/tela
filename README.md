# Tela Agent

An intelligent AI companion application built with LangGraph, featuring multi-modal interactions including text conversations, image generation, speech synthesis, and long-term memory management.

## Overview

Tela Agent is a sophisticated AI companion that can engage in natural conversations, generate images, process audio, and maintain context across sessions. The application uses a LangGraph-based workflow to intelligently route between different interaction modes (conversation, image generation, and audio responses) based on user input.

### Key Features

- **Multi-Modal Interactions**
  - Text conversations with context-aware responses
  - Image generation from text prompts
  - Image analysis and description
  - Speech-to-text transcription
  - Text-to-speech synthesis

- **Memory Management**
  - Short-term memory using SQLite for conversation context
  - Long-term memory using Qdrant vector store for persistent user information
  - Automatic conversation summarization
  - Context-aware memory retrieval

- **Multiple Interfaces**
  - **Chainlit Web Interface**: Interactive web-based chat interface
  - **Telegram Bot**: WhatsApp-like messaging interface

- **Intelligent Workflow Routing**
  - Automatic detection of user intent (conversation, image, or audio)
  - Context-aware activity scheduling
  - Dynamic workflow selection based on conversation history

## Architecture

The application is built using:

- **LangGraph**: Workflow orchestration and state management
- **LangChain**: LLM integration and chain building
- **FastAPI**: REST API framework for Telegram interface
- **Chainlit**: Web-based chat interface
- **Qdrant**: Vector database for long-term memory
- **SQLite**: Short-term conversation memory
- **Groq**: Text generation and speech-to-text
- **ElevenLabs**: Text-to-speech synthesis
- **Google Gemini**: Image generation

### Project Structure

```
tela-agent/
├── src/
│   └── ai_companion/
│       ├── core/              # Core utilities, prompts, exceptions
│       ├── graph/             # LangGraph workflow definition
│       │   ├── nodes.py       # Workflow nodes
│       │   ├── edges.py       # Workflow routing logic
│       │   └── state.py        # State management
│       ├── interfaces/         # User interfaces
│       │   ├── chainlit/      # Web interface
│       │   └── telegram/       # Telegram bot interface
│       ├── modules/           # Feature modules
│       │   ├── image/         # Image generation and analysis
│       │   ├── memory/        # Memory management
│       │   ├── speech/        # Speech processing
│       │   └── schedules/      # Activity scheduling
│       └── settings.py        # Configuration
├── compose.yaml               # Docker Compose configuration
├── Dockerfile                 # Dockerfile for Telegram service
├── Dockerfile.chainlit        # Dockerfile for Chainlit service
├── pyproject.toml             # Project dependencies
└── .env.example               # Environment variables template
```

## Prerequisites

- **Python**: 3.12.x
- **Docker** and **Docker Compose** (for containerized deployment)
- **API Keys**:
  - Groq API key ([Get one here](https://console.groq.com/))
  - ElevenLabs API key ([Get one here](https://elevenlabs.io/))
  - Google Gemini API key ([Get one here](https://aistudio.google.com/app/apikey))
  - Telegram Bot Token (for Telegram interface, get from [@BotFather](https://t.me/BotFather))

## Installation

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tela-agent
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and fill in your API keys
   ```

3. **Start the services**
   ```bash
   docker compose up --build
   ```

   This will start:
   - Qdrant vector database on port `6333`
   - Chainlit web interface on port `8000`
   - Telegram bot interface on port `8080`

4. **Access the application**
   - Chainlit interface: http://localhost:8000
   - Telegram bot: Configure webhook to point to your server

### Local Development

1. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start Qdrant locally** (if not using Docker)
   ```bash
   docker run -p 6333:6333 qdrant/qdrant:latest
   ```

4. **Run the Chainlit interface**
   ```bash
   chainlit run src/ai_companion/interfaces/chainlit/app.py --port 8000
   ```

5. **Run the Telegram interface** (in a separate terminal)
   ```bash
   uvicorn ai_companion.interfaces.telegram.webhook_endpoint:app --port 8080
   ```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

#### Required API Keys
- `GROQ_API_KEY`: Your Groq API key for text generation and speech-to-text
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key for text-to-speech
- `ELEVENLABS_VOICE_ID`: Voice ID for ElevenLabs TTS
- `GEMINI_API_KEY`: Your Google Gemini API key for image generation

#### Telegram Configuration (Required for Telegram interface)
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather
- `SECRET_WEBHOOK_TOKEN`: Secret token for webhook verification

#### Qdrant Configuration
- `QDRANT_URL`: Qdrant server URL (default: `http://qdrant:6333` for Docker, `http://localhost:6333` for local)
- `QDRANT_HOST`: Qdrant hostname (default: `qdrant` for Docker, `localhost` for local)
- `QDRANT_PORT`: Qdrant port (default: `6333`)
- `QDRANT_API_KEY`: Optional API key if Qdrant is configured with authentication

#### Optional Configuration
- Model names (see `.env.example` for defaults)
- Memory configuration parameters
- Database paths

See `.env.example` for a complete list of all available configuration options.

## Usage

### Chainlit Web Interface

1. Navigate to http://localhost:8000
2. Start chatting with Tela
3. Upload images for analysis
4. Request image generation by asking Tela to create images
5. Request audio responses by asking to hear Tela's voice

### Telegram Bot Interface

1. Create a bot using [@BotFather](https://t.me/BotFather)
2. Configure the webhook to point to your server:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-server.com/telegram_response.py", "secret_token": "YOUR_SECRET_TOKEN"}'
   ```
3. Start chatting with your bot on Telegram

## Workflow

The application uses a LangGraph-based workflow that:

1. **Extracts memories** from user messages
2. **Routes** to appropriate workflow (conversation, image, or audio)
3. **Injects context** including long-term memories and current activity
4. **Processes** the request through the selected workflow
5. **Summarizes** conversations when they exceed a certain length

### Workflow Nodes

- `memory_extraction_node`: Extracts important facts from user messages
- `router_node`: Determines the appropriate workflow (conversation/image/audio)
- `context_injection_node`: Injects schedule-based context
- `memory_injection_node`: Retrieves and injects relevant long-term memories
- `conversation_node`: Handles text-based conversations
- `image_node`: Generates images from text prompts
- `audio_node`: Generates audio responses

## Development

### Project Dependencies

The project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`.

### Running Tests

```bash
# Add test commands here when tests are implemented
```

### Code Structure

- **Graph Workflow**: Defined in `src/ai_companion/graph/`
- **Modules**: Feature implementations in `src/ai_companion/modules/`
- **Interfaces**: User-facing interfaces in `src/ai_companion/interfaces/`
- **Core**: Shared utilities, prompts, and exceptions in `src/ai_companion/core/`

## Docker Services

The `compose.yaml` file defines three services:

1. **qdrant**: Vector database for long-term memory storage
2. **chainlit**: Web-based chat interface
3. **telegram**: Telegram bot webhook endpoint

All services are configured to communicate with each other through Docker's internal network.

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all required API keys are set in `.env`
2. **Qdrant Connection Issues**: Verify Qdrant is running and accessible
3. **Port Conflicts**: Change port mappings in `compose.yaml` if ports are already in use
4. **Permission Errors**: Ensure volume mounts have correct permissions

### Logs

View Docker service logs:
```bash
docker compose logs -f [service-name]
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Uses [LangChain](https://github.com/langchain-ai/langchain) for LLM integration
- Powered by [Groq](https://groq.com/), [ElevenLabs](https://elevenlabs.io/), and [Google Gemini](https://deepmind.google/technologies/gemini/)

