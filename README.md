# RealTime Caption

A real-time captioning system that provides live captions for any tab in Chrome using audio transcription. The system combines a Chrome extension with a Python backend server to deliver accurate, low-latency captions.

## Features

- Real-time audio capture from any Chrome tab
- Low-latency transcription using Faster Whisper model
- Optional caption cleaning using OpenAI's GPT models
- Overlay captions on any webpage
- WebSocket-based audio streaming
- Server-Sent Events (SSE) for efficient caption delivery
- Configurable caption display styling

## Architecture

The project consists of two main components:

### 1. Chrome Extension
- Tab audio capture using Chrome's `tabCapture` API
- WebSocket client for streaming audio data
- Customizable caption overlay
- Simple control interface (start/stop buttons)

### 2. Python Backend
- WebSocket server for receiving audio streams
- Fast transcription using Faster Whisper model
- Optional text cleaning using OpenAI's GPT models
- Flask server with CORS support for caption delivery
- Server-Sent Events for efficient caption streaming

## Requirements

### Backend
- Python 3.x
- Flask
- Flask-CORS
- faster-whisper
- soundcard
- numpy
- websockets
- openai (optional, for caption cleaning)

### Frontend (Chrome Extension)
- Chrome browser
- Permissions for tab audio capture

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Satviik/RealTimeCaption.git
cd RealTimeCaption
```

2. Install Python dependencies:
```bash
pip install flask flask-cors faster-whisper soundcard numpy websockets openai
```

3. Install the Chrome extension:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chromeextension` folder from this repository

## Usage

1. Start the Python backend server:
```bash
python server.py
```

2. Click the extension icon in Chrome
3. Click "Start Tab Audio Capture" to begin capturing audio
4. Click "Start" to begin displaying captions
5. Click "Stop" to end the captioning session

## Configuration

### Caption Styling
You can customize the caption overlay appearance by modifying `chromeextension/style.css`.

### Audio Processing
Adjust audio processing parameters in `test.py`:
- `SAMPLE_RATE`: Audio sampling rate (default: 16000)
- `CHUNK_SEC`: Audio chunk size in seconds (default: 1.5)
- `OVERLAP_SEC`: Overlap between chunks (default: 0.2)

### OpenAI Integration
To enable caption cleaning with GPT:
1. Install the openai package: `pip install openai`
2. Set your OpenAI API key as an environment variable:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) for the transcription model
- OpenAI for the optional caption cleaning capability
