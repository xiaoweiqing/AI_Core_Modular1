# main.py
# AT THE TOP of main.py
from core import system_services
import os
import sys
import time
import threading
import subprocess
import pyperclip
from pathlib import Path
# AT THE TOP of main.py
from core import audio_services
# --- Dependency Checks ---
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("❌ Critical Error: 'watchdog' library not found. Please run 'pip install watchdog'.")

# --- Import Our Custom Modules ---
import config
from core import state
from core import ai_services
from core import database_manager
from core import hotkey_handlers # We will create the functions in this file next
from utils.helpers import Colors, safe_notification

# --- Hotkey Signal Handling ---

# In main.py, inside the FileTriggerHandler class

# REPLACE THE ENTIRE 'FileTriggerHandler' CLASS IN main.py WITH THIS BLOCK:

class FileTriggerHandler(FileSystemEventHandler):
    """Watches for the creation of trigger files and calls the corresponding function."""
    def __init__(self):
        self.function_map = {
            # --- AI Power Tools ---
            str(config.TRIGGER_FILES["translate_to_en"]): create_hotkey_handler(
                hotkey_handlers.translate_to_en
            ),
            str(config.TRIGGER_FILES["translate_to_zh"]): create_hotkey_handler(
                hotkey_handlers.translate_to_zh
            ),
            str(config.TRIGGER_FILES["optimize_prompt"]): create_hotkey_handler(
                hotkey_handlers.optimize_prompt
            ),
            str(config.TRIGGER_FILES["get_concise_answer"]): create_hotkey_handler(
                hotkey_handlers.get_concise_answer
            ),
            # --- Personal Security & Context ---
            str(config.TRIGGER_FILES["personal_risk_analysis"]): create_hotkey_handler(
                hotkey_handlers.personal_risk_analysis
            ),
            str(config.TRIGGER_FILES["export_range_context"]): create_hotkey_handler(
                hotkey_handlers.export_context_by_range
            ),
            # --- Data Mappings ---
            str(config.TRIGGER_FILES["save_input"]): create_hotkey_handler(
                hotkey_handlers.save_input
            ),
            str(config.TRIGGER_FILES["save_output"]): create_hotkey_handler(
                hotkey_handlers.save_output
            ),
            str(config.TRIGGER_FILES["cancel_turn"]): hotkey_handlers.cancel_last_turn,
            str(config.TRIGGER_FILES["mark_high_quality"]): hotkey_handlers.mark_as_high_quality,
            # --- Audio Mappings ---
            str(config.TRIGGER_FILES["read_aloud"]): create_hotkey_handler(
                hotkey_handlers.read_text_aloud
            ),
            str(config.TRIGGER_FILES["toggle_read_aloud"]): hotkey_handlers.toggle_read_aloud_mode,
            str(config.TRIGGER_FILES["voice_to_text"]): hotkey_handlers.voice_to_text_workflow,
            str(config.TRIGGER_FILES["meeting_mode"]): hotkey_handlers.toggle_meeting_mode,
            # --- Advanced Search Mappings ---
            str(config.TRIGGER_FILES["codebase_search"]): create_hotkey_handler(
                hotkey_handlers.search_codebase
            ),
            str(config.TRIGGER_FILES["personal_memory_advisor"]): create_hotkey_handler(
                hotkey_handlers.analyze_personal_history
            ),
            str(config.TRIGGER_FILES["talent_pool_search"]): create_hotkey_handler(
                hotkey_handlers.find_and_search_talent_pools
            ),
        }
        print(">> [System] Hotkey file watcher initialized.")

    def on_created(self, event):
        """Called when a file is created in the IPC directory."""
        if not event.is_directory and event.src_path in self.function_map:
            print(f"\n>> [Signal] Received task: {Path(event.src_path).name}")
            self.function_map[event.src_path]()
            try:
                time.sleep(0.1)
                os.unlink(event.src_path)
            except OSError:
                pass

def create_hotkey_handler(target_func, *args):
    """
    A wrapper function that retrieves selected text from the system
    before calling the actual target function (e.g., translate_to_en).
    """
    def handler():
        def task_with_selected_text():
            text_to_process = ""
            try:
                # Try to get highlighted text on X11
                text_to_process = subprocess.run(
                    ["xclip", "-o", "-selection", "primary"],
                    capture_output=True, text=True, check=True
                ).stdout
            except Exception:
                try:
                    # Try to get highlighted text on Wayland
                    text_to_process = subprocess.run(
                        ["wl-paste", "-p"], capture_output=True, text=True, check=True
                    ).stdout
                except Exception:
                    # Fallback to the general clipboard
                    text_to_process = ""

            # If no highlighted text, use the main clipboard content
            if not text_to_process or text_to_process.isspace():
                text_to_process = pyperclip.paste()

            if text_to_process and not text_to_process.isspace():
                # Call the intended function with the text
                if args:
                    target_func(text_to_process, *args)
                else:
                    target_func(text_to_process)
            else:
                safe_notification("No Text Found", "Please select or copy text first.")

        # Run the text retrieval and function call in a separate thread
        # to keep the main file watcher responsive.
        threading.Thread(target=task_with_selected_text, daemon=True).start()

    return handler


# --- Main Application Entry Point ---

# REPLACE the entire if __name__ == "__main__": block in main.py with this:

# --- Main Application Entry Point ---

if __name__ == "__main__":
    # 1. Initial Setup
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 70)
    print("      AI Core Modular - Bilingual Dialogue Turn Builder")
    print("=" * 70)

    if not WATCHDOG_AVAILABLE:
        sys.exit(1)

    # 2. Start Core Services
    if not ai_services.setup_api():
        sys.exit(1)
    if not database_manager.setup_all_databases():
        sys.exit(1)
    if not ai_services.setup_embedding_model():
        print(f"{Colors.YELLOW}Warning: Embedding model failed to load. Vector search will be disabled.{Colors.ENDC}")
    if not audio_services.setup_whisper_model():
        sys.exit(1)
    system_services.run_startup_maintenance()

    # 3. Start Background Threads
    print(">> [System] Starting background transcription processor...")
    threading.Thread(target=audio_services.processor_task, daemon=True).start()
    print("✅ [System] Background processor is running.")

    # 4. Setup IPC Directory for Hotkeys
    config.IPC_DIR.mkdir(exist_ok=True)
    for file_path in config.TRIGGER_FILES.values():
        if file_path.exists():
            file_path.unlink()

    # 5. Start the File Watcher
    observer = Observer()
    observer.schedule(FileTriggerHandler(), str(config.IPC_DIR), recursive=False)
    observer.start()
    print("✅ [System] Core services are running. Listening for hotkey signals...")

    # 6. Display User Instructions
    print("\n" + "=" * 70)
    print(f"  {Colors.GREEN}--- Language Learning & Tools ---{Colors.ENDC}")
    print(f"  - [Alt+R] -> {Colors.GREEN}Reads selected text aloud (EN/ZH Auto-Detect){Colors.ENDC}")
    print(f"  - [Alt+T] -> {Colors.YELLOW}Toggle [Translate & Read] Mode{Colors.ENDC}")
    print(f"  - [Alt+G] -> {Colors.CYAN}Record SHORT Voice to Text (Start/Stop){Colors.ENDC}")
    print(f"  - [Alt+B] -> {Colors.RED}TOGGLE Long-Form Meeting Recorder{Colors.ENDC}")
    print(f"\n  {Colors.GREEN}--- AI Power Tools ---{Colors.ENDC}")
    print(f"  - [Alt+Q] -> Translates selected text to {Colors.CYAN}English{Colors.ENDC}")
    print(f"  - [Alt+W] -> Translates selected text to {Colors.GREEN}Chinese{Colors.ENDC}")
    print(f"  - [Alt+E] -> {Colors.BLUE}Optimizes{Colors.ENDC} selected text into a high-quality prompt")
    print(f"  - [Alt+N] -> Gets a hyper-concise {Colors.YELLOW}answer{Colors.ENDC} for selected text")
    print(f"\n  {Colors.MAGENTA}--- Personal Security & Context ---{Colors.ENDC}")
    print(f"  - [Alt+Z] -> Analyzes text for personal {Colors.MAGENTA}risks & opportunities{Colors.ENDC}")
    print(f"\n  {Colors.MAGENTA}--- AI Training Data Center ---{Colors.ENDC}")
    print(f"  - [Alt+S] -> {Colors.MAGENTA}Saves Input{Colors.ENDC} to corpus.")
    print(f"  - [Alt+D] -> {Colors.MAGENTA}Saves Output{Colors.ENDC}, completes the pair.")
    print(f"  - [Alt+C] -> {Colors.YELLOW}Cancels{Colors.ENDC} the pending input.")
    print(f"  - [Alt+F] -> Marks the last pair as {Colors.BLUE}High-Quality{Colors.ENDC}.")
    print(f"\n  {Colors.BLUE}--- Advanced Search & Export ---{Colors.ENDC}")
    print(f"  - [Alt+J] -> {Colors.BLUE}Memory Advisor:{Colors.ENDC} Analyzes topic against your history")
    print(f"  - [Alt+K] -> {Colors.BLUE}Codebase Search:{Colors.ENDC} High-speed code search")
    print(f"  - [Alt+M] -> {Colors.BLUE}Talent Search:{Colors.ENDC} Scans all vector DBs for candidates")
    print(f"  - [Alt+V] -> {Colors.BLUE}Export History:{Colors.ENDC} Exports dialogue in a selected range")
    print("\n  Press Ctrl+C to safely exit the program.")
    print("=" * 70 + "\n")

    # 7. Keep the Application Alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n>> [System] Shutdown signal received, stopping services...")
    finally:
        observer.stop()
        observer.join()
        print(">> [System] Exited safely.")
