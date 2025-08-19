# FireRedASR API

A speech recognition API service with NVIDIA CUDA support.

## Features

- Support for NVIDIA CUDA acceleration
- Flask-based REST API
- Multiple ASR model support (AED and LLM)
- Audio file processing with VAD
- Docker containerization

## Quick Start

### Using Docker

```bash
# Build the image
docker build -t fireredasr-api .

# Run the container
docker run --gpus all -p 5078:5078 fireredasr-api
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## API Usage

### Transcription Endpoint

```bash
curl -X POST http://localhost:5078/v1/audio/transcriptions \
  -F "file=@audio.wav" \
  -F "model=AED"
```

## Docker Hub

Pre-built images are available on Docker Hub with CUDA support.

## License

MIT License