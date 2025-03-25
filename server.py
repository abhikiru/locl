from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import sqlite3
from pydantic import BaseModel
import time
import pyperclip
import threading
import sys

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite Database Setup
def init_db():
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, clipboard TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS history (username TEXT, text TEXT, timestamp INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS copied_text_history (username TEXT, text TEXT, timestamp INTEGER)''')
        conn.commit()
        conn.close()
        logger.info("[INFO] Database initialized successfully")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize database: {e}")

init_db()

# Pydantic models
class UserLogin(BaseModel):
    username: str
    password: str

class HistoryItem(BaseModel):
    text: str

# Get username from command-line argument, or use a default username
if len(sys.argv) == 2:
    USERNAME = sys.argv[1]
else:
    USERNAME = "testuser"  # Default username if none provided
    logger.warning("No username provided in command-line. Using default username: testuser")

# Clipboard Monitoring Logic (Merged from clipboard_monitor.py)
def update_copied_text(username, text):
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        # Insert new copied text into history
        c.execute("INSERT INTO copied_text_history (username, text, timestamp) VALUES (?, ?, ?)", (username, text, int(time.time())))
        conn.commit()

        # Enforce max 10 copied text history items
        c.execute("SELECT text FROM copied_text_history WHERE username = ? ORDER BY timestamp DESC", (username,))
        history_items = c.fetchall()
        if len(history_items) > 10:
            items_to_delete = len(history_items) - 10
            c.execute("DELETE FROM copied_text_history WHERE username = ? AND text IN (SELECT text FROM copied_text_history WHERE username = ? ORDER BY timestamp ASC LIMIT ?)", (username, username, items_to_delete))
            conn.commit()

        conn.close()
        logger.info(f"[INFO] Copied text history updated for user {username}: {text}")
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while updating copied text history: {e}")

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
                    update_copied_text(USERNAME, current_clipboard_content)
            time.sleep(0.5)  # Check every 0.5 seconds
        except Exception as e:
            logger.error(f"Error monitoring clipboard: {e}")
            time.sleep(1)  # Wait before retrying

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html file
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    logger.info("[INFO] Serving index.html")
    try:
        with open("templates/index.html", "r") as file:
            content = file.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        logger.error("[ERROR] index.html not found in templates folder")
        return HTMLResponse(content="<h1>index.html not found in templates folder</h1>", status_code=404)

# API endpoint to login
@app.post("/login")
async def login(user: UserLogin):
    logger.info(f"[INFO] Login attempt for user: {user.username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (user.username, user.password))
        result = c.fetchone()
        if result:
            logger.info(f"[INFO] User {user.username} logged in successfully")
            conn.close()
            return {"status": "success", "message": "Login successful"}
        else:
            c.execute("INSERT INTO users (username, password, clipboard) VALUES (?, ?, ?)", (user.username, user.password, ""))
            conn.commit()
            logger.info(f"[INFO] New user {user.username} registered")
            conn.close()
            return {"status": "success", "message": "User registered and logged in"}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred during login: {e}")
        raise HTTPException(status_code=500, detail="Failed to process login")

# API endpoint to update clipboard (Clipboard Manager)
@app.post("/update-clipboard")
async def update_clipboard(request: Request):
    logger.info("[INFO] Received request to update clipboard")
    try:
        data = await request.json()
        username = data.get("username")
        text = data.get("text", "")

        if not username or not text:
            logger.warning("[WARNING] Username or text missing in request")
            raise HTTPException(status_code=400, detail="Username and text are required")

        # Update the database
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("UPDATE users SET clipboard = ? WHERE username = ?", (text, username))
        conn.commit()
        conn.close()

        # Copy the text to the server's system clipboard
        try:
            pyperclip.copy(text)
            logger.info(f"[INFO] Text copied to server's system clipboard: {text}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to copy text to server's system clipboard: {e}")

        logger.info(f"[INFO] Clipboard updated for user {username}: {text}")
        return {"status": "success", "message": "Clipboard updated"}

    except ValueError:
        logger.error("[ERROR] Invalid JSON payload received")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while updating clipboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to update clipboard")

# API endpoint to fetch clipboard (Clipboard Manager)
@app.get("/fetch-clipboard/{username}")
async def fetch_clipboard(username: str):
    logger.info(f"[INFO] Fetching clipboard for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT clipboard FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()

        if result and result[0]:
            logger.info(f"[INFO] Clipboard content fetched for user {username}: {result[0]}")
            return {"status": "success", "text": result[0]}
        else:
            logger.warning(f"[WARNING] No clipboard content found for user {username}")
            return {"status": "error", "message": "No clipboard content found"}

    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while fetching clipboard: {e}")
        return {"status": "error", "message": "Failed to fetch clipboard"}

# API endpoint to fetch copied text history (System-wide Ctrl+C)
@app.get("/fetch-copied-text/{username}")
async def fetch_copied_text(username: str):
    logger.info(f"[INFO] Fetching copied text history for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT text FROM copied_text_history WHERE username = ? ORDER BY timestamp DESC", (username,))
        history_items = [row[0] for row in c.fetchall()]
        conn.close()
        logger.info(f"[INFO] Copied text history fetched for user {username}: {history_items}")
        return {"status": "success", "history": history_items}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while fetching copied text history: {e}")
        return {"status": "error", "message": "Failed to fetch copied text history"}

# API endpoint to delete copied text history item
@app.post("/delete-copied-text/{username}")
async def delete_copied_text(username: str, item: HistoryItem):
    logger.info(f"[INFO] Deleting copied text history item for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("DELETE FROM copied_text_history WHERE username = ? AND text = ?", (username, item.text))
        conn.commit()
        conn.close()
        logger.info(f"[INFO] Copied text history item deleted for user {username}: {item.text}")
        return {"status": "success", "message": "Copied text history item deleted"}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while deleting copied text history: {e}")
        return {"status": "error", "message": "Failed to delete copied text history"}

# API endpoint to clear copied text history
@app.post("/clear-copied-text/{username}")
async def clear_copied_text(username: str):
    logger.info(f"[INFO] Clearing copied text history for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("DELETE FROM copied_text_history WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        logger.info(f"[INFO] Copied text history cleared for user {username}")
        return {"status": "success", "message": "Copied text history cleared"}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while clearing copied text history: {e}")
        return {"status": "error", "message": "Failed to clear copied text history"}

# API endpoint to update history (Clipboard Manager)
@app.post("/update-history/{username}")
async def update_history(username: str, item: HistoryItem):
    logger.info(f"[INFO] Updating history for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO history (username, text, timestamp) VALUES (?, ?, ?)", (username, item.text, int(time.time())))
        conn.commit()

        # Enforce max 10 history items
        c.execute("SELECT text FROM history WHERE username = ? ORDER BY timestamp DESC", (username,))
        history_items = c.fetchall()
        if len(history_items) > 10:
            items_to_delete = len(history_items) - 10
            c.execute("DELETE FROM history WHERE username = ? AND text IN (SELECT text FROM history WHERE username = ? ORDER BY timestamp ASC LIMIT ?)", (username, username, items_to_delete))
            conn.commit()

        conn.close()
        logger.info(f"[INFO] History updated for user {username}")
        return {"status": "success", "message": "History updated"}

    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while updating history: {e}")
        raise HTTPException(status_code=500, detail="Failed to update history")

# API endpoint to fetch history (Clipboard Manager)
@app.get("/fetch-history/{username}")
async def fetch_history(username: str):
    logger.info(f"[INFO] Fetching history for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT text FROM history WHERE username = ? ORDER BY timestamp DESC", (username,))
        history_items = [row[0] for row in c.fetchall()]
        conn.close()
        logger.info(f"[INFO] History fetched for user {username}: {history_items}")
        return {"status": "success", "history": history_items}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while fetching history: {e}")
        return {"status": "error", "message": "Failed to fetch history"}

# API endpoint to delete history item (Clipboard Manager)
@app.post("/delete-history/{username}")
async def delete_history(username: str, item: HistoryItem):
    logger.info(f"[INFO] Deleting history item for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("DELETE FROM history WHERE username = ? AND text = ?", (username, item.text))
        conn.commit()
        conn.close()
        logger.info(f"[INFO] History item deleted for user {username}: {item.text}")
        return {"status": "success", "message": "History item deleted"}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while deleting history: {e}")
        return {"status": "error", "message": "Failed to delete history"}

# API endpoint to clear history (Clipboard Manager)
@app.post("/clear-history/{username}")
async def clear_history(username: str):
    logger.info(f"[INFO] Clearing history for user: {username}")
    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("DELETE FROM history WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        logger.info(f"[INFO] History cleared for user {username}")
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        logger.error(f"[ERROR] Exception occurred while clearing history: {e}")
        return {"status": "error", "message": "Failed to clear history"}

# API endpoint to test server health
@app.get("/health")
async def health_check():
    logger.info("[INFO] Health check requested")
    return {"status": "success", "message": "Server is running"}

# Main execution
if __name__ == "__main__":
    import uvicorn
    # Start the clipboard monitoring in a separate thread
    clipboard_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    clipboard_thread.start()
    # Start the FastAPI server
    logger.info("[INFO] Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8010)