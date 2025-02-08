#!/bin/bash

echo "Starting Telegram bot..."

# Install dependencies
pip install -r requirements.txt

# Start the bot in the background
python yt_video_uploader.py &

# Start a simple HTTP server to keep the service alive
python -m http.server ${PORT:-8080}
