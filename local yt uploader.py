import os
import logging
import pickle
import re  # ✅ Import regex for filename cleaning
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request  # ✅ Fix for "Request is not defined"
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from telethon import TelegramClient, events

# ✅ Telegram API credentials
API_ID = "26343896"  # Get from https://my.telegram.org
API_HASH = "4396c576cb87d17d98c5b74aeeb315dc"  # Get from https://my.telegram.org
CHANNEL_USERNAME = "@ytvideotester"  # Your Telegram channel username

# ✅ YouTube API credentials
CLIENT_SECRETS_FILE = r"E:\Yt video uploader\credentials.json"
TOKEN_FILE = "token.json"  # Stores authentication token
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# ✅ Logging
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

# ✅ Upload video to YouTube
def upload_to_youtube(file_path, title, description, tags):
    youtube = get_authenticated_service()
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",  # 22 = "People & Blogs"
        },
        "status": {
            "privacyStatus": "public",  # Change to "private" or "unlisted" if needed
        },
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

# ✅ Sanitize filenames
def sanitize_filename(title):
    """Remove invalid characters from the title to make a valid filename."""
    title = re.sub(r'[<>:"/\\|?*\n]+', '', title)  # Remove special characters
    return title.strip()[:100] or "Untitled Video"  # Limit to 100 chars

# ✅ Handle new video messages from Telegram
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

# ✅ Run the bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
