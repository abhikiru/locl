from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
import threading
import subprocess


class SimpleTerminalApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        # Log display area
        self.log_display = TextInput(
            readonly=True,
            background_color=(0, 0, 0, 1),
            foreground_color=(1, 1, 1, 1),
            font_name="RobotoMono-Regular",
            size_hint=(1, 0.8),
        )
        self.add_widget(self.log_display)

        # Buttons for server and typer
        button_layout = BoxLayout(size_hint=(1, 0.2))
        self.add_widget(button_layout)

        # Start/Stop Server Button
        self.server_button = Button(text="Start Server", background_color=(0, 1, 0, 1))
        self.server_button.bind(on_press=self.toggle_server)
        button_layout.add_widget(self.server_button)

        # Start/Stop Typer Button
        self.typer_button = Button(text="Start Typer", background_color=(0, 1, 0, 1))
        self.typer_button.bind(on_press=self.toggle_typer)
        button_layout.add_widget(self.typer_button)

        # Variables to manage threads
        self.server_thread = None
        self.typer_thread = None
        self.server_running = False
        self.typer_running = False

    def log_message(self, message):
        """Log a message in the terminal display on the main thread."""
        def update_log_display(dt):
            self.log_display.text += f"{message}\n"
            self.log_display.cursor = (0, len(self.log_display.text))  # Auto-scroll

        Clock.schedule_once(update_log_display)

    def toggle_server(self, _):
        """Start or stop the server."""
        if not self.server_running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.server_running = True
            self.server_button.text = "Stop Server"
            self.server_button.background_color = (1, 0, 0, 1)
        else:
            self.server_running = False
            self.log_message("[INFO] Stopping server...")
            self.server_button.text = "Start Server"
            self.server_button.background_color = (0, 1, 0, 1)

    def run_server(self):
        """Run the FastAPI server."""
        self.log_message("[INFO] Starting server...")
        try:
            process = subprocess.Popen(
                ["python", "server.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            while self.server_running:
                line = process.stdout.readline()
                if line:
                    self.log_message(line.strip())
                error_line = process.stderr.readline()
                if error_line:
                    self.log_message(f"[ERROR] {error_line.strip()}")
            process.terminate()
            self.log_message("[INFO] Server stopped.")
        except Exception as e:
            self.log_message(f"[ERROR] Exception while running server: {e}")

    def toggle_typer(self, _):
        """Start or stop the typer."""
        if not self.typer_running:
            self.typer_thread = threading.Thread(target=self.run_typer, daemon=True)
            self.typer_thread.start()
            self.typer_running = True
            self.typer_button.text = "Stop Typer"
            self.typer_button.background_color = (1, 0, 0, 1)
        else:
            self.typer_running = False
            self.log_message("[INFO] Stopping typer...")
            self.typer_button.text = "Start Typer"
            self.typer_button.background_color = (0, 1, 0, 1)

    def run_typer(self):
        """Run the typer script continuously until stopped by the user."""
        self.log_message("[INFO] Starting typer...")

        while self.typer_running:
            try:
                # Start typer.py as a subprocess
                process = subprocess.Popen(
                    ["python", "typer.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )

                # Use a separate thread to read stdout and stderr concurrently
                def read_output(pipe, log_prefix):
                    while True:
                        line = pipe.readline()
                        if line == "" and process.poll() is not None:
                            break  # Exit loop if process ends
                        if line.strip():
                            self.log_message(f"{log_prefix} {line.strip()}")

                stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "[STDOUT]"), daemon=True)
                stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "[STDERR]"), daemon=True)
                stdout_thread.start()
                stderr_thread.start()

                # Wait for the process to finish
                process.wait()
                stdout_thread.join()
                stderr_thread.join()

                # If typer_running is still True, it means typer.py crashed or stopped unexpectedly
                if self.typer_running:
                    self.log_message("[WARNING] Typer script stopped unexpectedly. Restarting...")

            except Exception as e:
                self.log_message(f"[ERROR] Exception in run_typer: {e}")
                break

        self.log_message("[INFO] Typer stopped.")


class MainApp(App):
    def build(self):
        return SimpleTerminalApp()


if __name__ == "__main__":
    MainApp().run()
