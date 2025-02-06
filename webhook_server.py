from flask import Flask, request
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Webhook Server Running!"

@app.route('/webhook', methods=['POST'])
def run_script():
    """Trigger the YouTube uploader when the webhook is called."""
    try:
        subprocess.Popen(["python3", "YT_VIDEO_UPLOADER.py"])
        return "Upload started!", 200
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 8443))  # Get PORT from environment variable or default to 8443
    app.run(host='0.0.0.0', port=PORT)
