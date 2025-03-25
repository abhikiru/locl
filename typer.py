import keyboard
import pyperclip
import time
import threading

# Global variables
script_text = ""  # Clipboard content
text_index = 0      # Current typing position
auto_typing = False # Automatic typing toggle

# Lock for clipboard access
clipboard_lock = threading.Lock()

# Function to monitor clipboard for updates
def monitor_clipboard():
    global script_text, text_index
    while True:
        with clipboard_lock:
            new_text = pyperclip.paste()  # Get current clipboard content
            if new_text != script_text:  # Update only if clipboard text has changed
                script_text = new_text
                text_index = 0  # Reset position when clipboard updates
                print(f"[DEBUG] Clipboard updated in typer.py: {script_text}")
        time.sleep(0.5)  # Check every 500ms

# Function to type one character at a time
def type_one_character():
    global text_index, script_text
    if text_index < len(script_text):
        char_to_type = script_text[text_index]
        try:
            keyboard.write(char_to_type)  # Simulate typing the character
            print(f"[DEBUG] Typed: {char_to_type}")  # Debug log for each character
            text_index += 1
            time.sleep(0.01)  # Add a slight delay between keystrokes
        except Exception as e:
            print(f"[ERROR] Error typing character '{char_to_type}': {e}")
    else:
        print("[DEBUG] Typing complete.")
        keyboard.write("\n")  # Add a newline after completion
        text_index = 0  # Reset for next typing

# Function for automatic typing
def automatic_typing():
    global auto_typing, text_index, script_text
    while auto_typing:
        if text_index < len(script_text):
            char_to_type = script_text[text_index]
            keyboard.write(char_to_type)
            text_index += 1
            time.sleep(0.3)  # Typing delay
        else:
            auto_typing = False  # Stop when typing is complete
            print("[DEBUG] Automatic typing complete.")
            keyboard.write("\n")  # Add a newline after completion
            text_index = 0  # Reset for next typing

# Function to toggle automatic typing
def toggle_auto_typing():
    global auto_typing
    if not auto_typing:
        auto_typing = True
        print("[DEBUG] Automatic typing started.")
        threading.Thread(target=automatic_typing, daemon=True).start()
    else:
        auto_typing = False
        print("[DEBUG] Automatic typing stopped.")

# Function to reset typing to the beginning
def reset_typing():
    global text_index
    text_index = 0
    print("[DEBUG] Typing reset to the beginning.")

# Thread to handle clipboard monitoring
def start_clipboard_monitor():
    monitor_thread = threading.Thread(target=monitor_clipboard, daemon=True)
    monitor_thread.start()

# Keyboard hotkey setup
keyboard.add_hotkey('insert', type_one_character)  # Manual character-by-character typing
keyboard.add_hotkey('ctrl+b', toggle_auto_typing)  # Start/stop automatic typing
keyboard.add_hotkey('$', lambda: toggle_auto_typing() if auto_typing else None)  # Stop automatic typing with $
keyboard.add_hotkey('ctrl+m', reset_typing)  # Reset typing to the beginning

# Main execution
if __name__ == "__main__":
    print("[INFO] Typing script initialized.")
    print("Press 'Insert' to type one character at a time from the clipboard.")
    print("Press 'Ctrl+B' to start/stop automatic typing.")
    print("Press '$' to stop automatic typing.")
    print("Press 'Ctrl+M' to reset typing to the beginning.")

    # Start clipboard monitoring
    start_clipboard_monitor()
    try:
        while True:
            time.sleep(1)  # Prevent high CPU usage
    except KeyboardInterrupt:
        print("[INFO] Typing script terminated.")

    # Keep the script running
    keyboard.wait('ctrl+q')  # Exit on 'Ctrl+Q'
