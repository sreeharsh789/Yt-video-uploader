import os
import logging
import base64
import json
import re
import subprocess
import asyncio
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import events

# ✅ Load API keys from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# ✅ Load Google Service Account credentials from environment variable
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if GOOGLE_CREDENTIALS:
    credentials_json = json.loads(base64.b64decode(GOOGLE_CREDENTIALS).decode("utf-8"))
    with open("service_account.json", "w") as f:
        json.dump(credentials_json, f)  # Save credentials to file
else:
    raise Exception("❌ Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ✅ Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Authenticate and get YouTube API service
def get_authenticated_service():
    creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(file_path, title, description, tags):
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public"},
    }

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True),
        )

        response = request.execute()
        logger.info(f"✅ Video uploaded successfully: https://www.youtube.com/watch?v={response['id']}")
        return response

    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {e}")
        return None

def sanitize_filename(title):
    """Remove invalid characters from the title to make a valid filename."""
    title = re.sub(r'[<>:"/\\|?*\n]+', '', title)
    return title.strip()[:100] or "Untitled Video"

async def handle_new_message(event):
    if event.video:
        logger.info("📥 New video detected. Downloading...")

        title = event.message.text if event.message.text else "Untitled Video"
        title = sanitize_filename(title)

        file_path = f"{title}.mp4"
        await event.download_media(file=file_path)

        logger.info("📤 Uploading to YouTube...")
        description = "Uploaded from Telegram"
        tags = ["Telegram", "AutoUpload", "PythonBot"]

        upload_to_youtube(file_path, title, description, tags)

        os.remove(file_path)  # Cleanup after upload
        logger.info("🗑️ Deleted local file after upload.")

def convert_video_to_mp4(input_file):
    """Convert video to standard MP4 format using ffmpeg."""
    output_file = "converted.mp4"
    command = f'ffmpeg -i "{input_file}" -c:v libx264 -preset fast -c:a aac -b:a 128k "{output_file}" -y'
    subprocess.run(command, shell=True)
    return output_file

# ✅ Start the Telegram client with Session String
async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    channel = await client.get_entity(CHANNEL_USERNAME)

    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        await handle_new_message(event)

    logger.info("📡 Listening for new videos in the channel...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
