import time
import threading
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyautogui
import pytchat
import pygetwindow as gw

# --- 1. GLOBAL SETTINGS (CHANGE DIS!) i wanna slit my wrist so much lol 2.03am 23.10.25 ---
# Delay betwn keypresses (typing speed)
TYPING_INTERVAL = 0.1
# Text b4 the username (like 'Recorded: ')
PREFIX = "Recorded: "
# Bot RUN/STOP flag
bot_running = False
# Users already processed (no re-typing)
processed_users = set()
# App root reference for threads
app_root = None


# --- 2. BOT BRAIN (CORE LOGIC) ---

def erase_text(length):
    """Hit Backspace 'length' times."""
    if length <= 0:
        return

    # Mash that Backspace button
    pyautogui.press('backspace', presses=length, interval=0.01)


def type_name_and_erase(username, window_title):
    """Find window, type name, hit Backspace a lot."""
    global app_root

    text_to_type = PREFIX + username

    # --- STEP 1: FIND & ACTIVATE WINDOW ---
    try:
        # Get the window by its title string
        window = gw.getWindowsWithTitle(window_title)
        if not window:
            app_root.safe_log(f"❌ ERROR: Window '{window_title}' NOT found! Skippin.")
            return

        # Make it the active window (bring to front)
        window[0].activate()
        app_root.safe_log(f"✅ Window '{window_title}' activated.")
        # Wait a sec for the PC to switch
        time.sleep(0.3)

    except Exception as e:
        app_root.safe_log(f"❌ Error activating window: {e}")
        return  # Give up if switch fails

    # --- STEP 2: TYPE AND ERASE ---

    # Type the whole name using keyboard
    pyautogui.write(text_to_type, interval=TYPING_INTERVAL)
    app_root.safe_log(f"→ Typed: '{text_to_type}'")

    # Erase everything typed
    erase_text(len(text_to_type))

    log_message = f"✅ PROCESSED: '{username}' (Typed & erased)."
    app_root.safe_log(log_message)


def chat_monitor_thread(live_id, window_title):
    """Thread for readin YouTube chat."""
    global bot_running, processed_users, app_root

    try:
        # Start chat reader
        chat = pytchat.create(video_id=live_id)
        app_root.safe_log(f"✅ Connected to chat ID: {live_id}")
    except Exception as e:
        app_root.safe_log(f"❌ Error connecting to YouTube.")
        app_root.stop_bot()
        return

    while bot_running and chat.is_alive():
        try:
            for c in chat.get().items:
                if not bot_running:
                    break

                username = c.author.name

                # If seen b4, ignore
                if username in processed_users:
                    continue

                # New user! Add to list
                processed_users.add(username)

                # Start typing job in a new thread
                typing_thread = threading.Thread(
                    target=type_name_and_erase,
                    args=(username, window_title,),
                    daemon=True
                )
                typing_thread.start()

        except Exception as e:
            if bot_running:
                app_root.safe_log(f"⚠️ Chat error, retry in 3 sec: {e}")
            time.sleep(3)

    app_root.safe_log("🛑 Chat monitor stopped.")


# --- 3. THE BUTTONS AND BOXES (GUI) ---

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        global app_root
        app_root = self

        self.title("Dumb Typing Bot (Auto-Switch)")
        self.geometry("480x500")
        self.resizable(False, True)

        # Variables
        self.live_id_var = tk.StringVar(value="")
        self.window_title_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="STOPPED")
        self.chat_thread = None

        self.create_widgets()

    def create_widgets(self):
        # Settings Box
        settings_frame = ttk.LabelFrame(self, text="Settings", padding="10")
        settings_frame.pack(padx=10, pady=10, fill="x")

        # Live ID Input
        ttk.Label(settings_frame, text="1. YT Live ID (v=...):").grid(row=0, column=0, sticky="w", pady=5)
        self.id_entry = ttk.Entry(settings_frame, textvariable=self.live_id_var, width=35)
        self.id_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.id_entry.insert(0, "e.g. dFg5hJk1LpQ")

        # Window Title Input
        ttk.Label(settings_frame, text="2. EXACT Game Window Title:").grid(row=1, column=0, sticky="w", pady=5)
        self.title_entry = ttk.Entry(settings_frame, textvariable=self.window_title_var, width=35)
        self.title_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.title_entry.insert(0, "e.g. Notepad")

        # Buttons
        self.start_button = ttk.Button(settings_frame, text="3. START", command=self.start_bot)
        self.start_button.grid(row=2, column=0, sticky="ew", pady=10)

        self.stop_button = ttk.Button(settings_frame, text="STOP", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1, sticky="ew", padx=5, pady=10)

        # Status
        ttk.Label(self, text="Current Status:").pack(pady=(0, 5))
        self.status_label = ttk.Label(self, textvariable=self.status_var, font=('Arial', 14, 'bold'), foreground="red")
        self.status_label.pack(pady=(0, 10))

        # Log Console
        ttk.Label(self, text="Event Log:").pack(pady=(0, 5), padx=10, anchor="w")
        self.log_text = scrolledtext.ScrolledText(self, width=55, height=15, state=tk.DISABLED, wrap=tk.WORD,
                                                  font=('Courier New', 9))
        self.log_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.safe_log("App ready. Enter IDs & Titles.")

    def safe_log(self, message):
        """Put message in log, safe for threads."""
        # Use after() to run log update on main thread
        self.after(0, self._actual_log, message)

    def _actual_log(self, message):
        """Internal log function."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def start_bot(self):
        """Start chat monitoring thread."""
        global bot_running, processed_users

        live_id = self.live_id_var.get().strip()
        window_title = self.window_title_var.get().strip()

        # Simple input validation
        if not live_id or "Example" in live_id:
            self.safe_log("❌ ERROR: Need good YT Live ID.")
            return
        if not window_title or "Example" in window_title:
            self.safe_log("❌ ERROR: Need EXACT Window Title.")
            return

        bot_running = True
        processed_users.clear()

        # Update UI status
        self.status_var.set("RUNNING")
        self.status_label.config(foreground="green")
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.safe_log(f"🚀 Starting bot for ID: {live_id}")
        self.safe_log(f"🔍 Target window: '{window_title}'")
        self.safe_log(f"--- BOT ACTIVE. WAIT FOR CHAT MESSAGES ---")

        # Start chat reader in background thread
        self.chat_thread = threading.Thread(
            target=chat_monitor_thread,
            args=(live_id, window_title),
            daemon=True
        )
        self.chat_thread.start()

    def stop_bot(self):
        """Stop chat monitoring thread."""
        global bot_running

        if bot_running:
            messagebox.showinfo("Stopping", "Stopping bot. Wait a few secs for current process to finish.")

        bot_running = False

        # Update UI status
        self.status_var.set("STOPPED")
        self.status_label.config(foreground="red")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        self.safe_log("🛑 Bot stopped by user.")

    def on_closing(self):
        """Handle window closing."""
        self.stop_bot()
        # Wait a moment for threads to close before destroying app
        self.after(500, self.destroy)


if __name__ == "__main__":
    app = Application()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()