import os
import logging
import pickle
import base64
import re  # ✅ Import regex for filename cleaning
import subprocess
import asyncio
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from telethon import TelegramClient, events

# ✅ Load API keys from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# ✅ Load Google credentials from environment variable
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
if GOOGLE_CREDENTIALS:
    credentials_json = base64.b64decode(GOOGLE_CREDENTIALS).decode("utf-8")
    with open("credentials.json", "w") as f:
        f.write(credentials_json)  # Save credentials.json for use
    CLIENT_SECRETS_FILE = "credentials.json"
else:
    raise Exception("Missing GOOGLE_CREDENTIALS environment variable")

TOKEN_FILE = "token.json"  # Stores authentication token
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Authenticate and get YouTube API service
def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):  # Reuse existing credentials
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

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
    title = re.sub(r'[<>:"/\\|?*\n]+', '', title)  # Remove special characters
    return title.strip()[:100] or "Untitled Video"  # Limit to 100 chars

async def handle_new_message(event):
    if event.video:
        logger.info("📥 New video detected. Downloading...")

        # ✅ Use Telegram caption as title if available
        title = event.message.text if event.message.text else "Untitled Video"
        title = sanitize_filename(title)  # ✅ Clean the title

        file_path = f"{title}.mp4"
        await event.download_media(file=file_path)

        logger.info("📤 Uploading to YouTube...")
        description = "Uploaded from Telegram"
        tags = ["Telegram", "AutoUpload", "PythonBot"]

        upload_to_youtube(file_path, title, description, tags)

        os.remove(file_path)  # Clean up after upload
        logger.info("🗑️ Deleted local file after upload.")

def convert_video_to_mp4(input_file):
    """Convert video to standard MP4 format using ffmpeg."""
    output_file = "converted.mp4"
    command = f'ffmpeg -i "{input_file}" -c:v libx264 -preset fast -c:a aac -b:a 128k "{output_file}" -y'
    subprocess.run(command, shell=True)
    return output_file

# ✅ Start the Telegram client
async def main():
    client = TelegramClient("session_name", API_ID, API_HASH)
    await client.start()

    channel = await client.get_entity(CHANNEL_USERNAME)

    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        await handle_new_message(event)

    logger.info("📡 Listening for new videos in the channel...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
