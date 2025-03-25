import pyperclip
import requests
import time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("clipboard_monitor")

# Server URL and username
SERVER_URL = "http://127.0.0.1:8000"  # Update this if the server is running on a different host/port
USERNAME = "testuser"  # Replace with the username of the logged-in user

def send_to_server(text):
    try:
        response = requests.post(
            f"{SERVER_URL}/update-copied-text",
            json={"username": USERNAME, "text": text},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            logger.info(f"Successfully sent copied text to server: {text}")
        else:
            logger.error(f"Failed to send copied text to server: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending copied text to server: {e}")

def monitor_clipboard():
    logger.info("Starting clipboard monitoring...")
    last_clipboard_content = pyperclip.paste()  # Initial clipboard content

    while True:
        try:
            current_clipboard_content = pyperclip.paste()
            if current_clipboard_content != last_clipboard_content:
                logger.info(f"Clipboard changed: {current_clipboard_content}")
                last_clipboard_content = current_clipboard_content
                if current_clipboard_content:  # Only send non-empty text
                    send_to_server(current_clipboard_content)
            time.sleep(0.5)  # Check every 0.5 seconds
        except Exception as e:
            logger.error(f"Error monitoring clipboard: {e}")
            time.sleep(1)  # Wait before retrying

if __name__ == "__main__":
    monitor_clipboard()