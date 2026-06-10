# AI Companion Terminal Prototype

A Python-based creative AI interaction system designed for lectures, presentations, or performative research. It features voice input, natural text-to-speech output, context-aware memory, and computer vision triggers.

## Key Features

- **Interactive Voice Loop**: Conversational engagement via speech-to-text and text-to-speech.
- **Push-to-Talk Interaction**: Keyboard-triggered microphone captures to prevent false activations.
- **Smart Conversational Engine**: Powered by Groq API (extremely low latency LLM response).
- **Natural Voice Generation**: Powered by ElevenLabs API.
- **Computer Vision Context**: Uses OpenCV to detect faces and movement, adding context to the AI's prompts.
- **Structured Workspace**: Well-isolated directory structure following professional modular Python application architecture.

## Folder Structure

```
ai-companion-terminal/
│
├── main.py                     # Entry point
├── requirements.txt            # Project dependencies
├── .env                        # Configuration file (keys go here)
├── .env.example                # Configuration template
├── README.md                   # Setup and usage guide
│
├── app/
│   ├── __init__.py
│   ├── config.py               # Config loader and validator
│   ├── state.py                # Global state manager
│   │
│   ├── core/
│   │   ├── interaction_loop.py # Main loop logic (idle, listen, process, speak)
│   │   ├── prompt_builder.py   # System rules & personality builder
│   │   └── session_memory.py   # Conversation history manager
│   │
│   ├── services/
│   │   ├── groq_service.py     # LLM API connection (Groq)
│   │   ├── elevenlabs_service.py # Text-To-Speech (ElevenLabs)
│   │   ├── speech_service.py   # Microphone transcription (SpeechRecognition)
│   │   ├── vision_service.py   # Face and motion detection (OpenCV)
│   │   └── audio_player.py     # Wave/mp3 output player (Pygame)
│   │
│   ├── prompts/
│   │   ├── character_prompt.txt # AI persona and backstory
│   │   └── system_rules.txt     # AI interaction boundaries
│   │
│   └── utils/
│       ├── logger.py           # Logging mechanism
│       ├── file_manager.py     # Temporary audio and image management
│       └── terminal_ui.py      # Rich interface logs and states
│
└── assets/                     # Media output files
```

## Setup Instructions

### 1. Requirements

- Python 3.10+
- An active Internet connection (for Groq & ElevenLabs APIs)
- A working microphone and camera

### 2. Installation

Install PyAudio and other dependencies:

```bash
pip install -r requirements.txt
```

*Note for Windows users: If you run into issues installing `PyAudio`, you can download the appropriate precompiled wheel from [Unofficial Windows Binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) or install it via `pip install pipwin` followed by `pipwin install pyaudio`.*

### 3. API Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Fill in the credentials in `.env`:
- `GROQ_API_KEY`: Get it from [Groq Console](https://console.groq.com/).
- `ELEVENLABS_API_KEY`: Get it from [ElevenLabs Profile Settings](https://elevenlabs.io/).
- `ELEVENLABS_VOICE_ID`: Choose a voice ID from ElevenLabs.

### 4. Running the App

```bash
python main.py
```
By default, the application runs in text-only mode if no speech keys are specified.
Press **Enter** to trigger the voice capture / push-to-talk mechanism.
Use **Ctrl+C** to safely exit.
