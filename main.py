# main.py (CORRECTED)

import os
import sys
import asyncio
import threading
import subprocess
import pyperclip
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("❌ Critical Error: 'watchdog' library not found. Please run 'pip install watchdog'.")

from config import settings, TRIGGER_FILES
from core import state
from core import ai_services
from core import audio_services
from core import database_manager
from core import system_services
from core import hotkey_handlers
from utils.helpers import Colors, safe_notification
import traceback # <--- 【【【 在这里添加这一行 】】】
# In main.py
# REPLACE the entire AsyncFileTriggerHandler class with this corrected version.

# In main.py
# REPLACE the entire AsyncFileTriggerHandler class with this corrected version.

class AsyncFileTriggerHandler(FileSystemEventHandler):
    """
    [ASYNC] Watches for trigger files and calls the corresponding async function.
    [MODIFIED] Now includes the new Power Search feature.
    """
    def __init__(self, loop):
        self.loop = loop
        self.function_map = {
            # --- AI Power Tools ---
            str(TRIGGER_FILES["translate_to_en"]): create_async_hotkey_handler(
                hotkey_handlers.translate_to_en
            ),
            str(TRIGGER_FILES["translate_to_zh"]): create_async_hotkey_handler(
                hotkey_handlers.translate_to_zh
            ),
            str(TRIGGER_FILES["optimize_prompt"]): create_async_hotkey_handler(
                hotkey_handlers.optimize_prompt
            ),
            str(TRIGGER_FILES["get_concise_answer"]): create_async_hotkey_handler(
                hotkey_handlers.get_concise_answer
            ),
            # --- Personal Security & Context ---
            str(TRIGGER_FILES["personal_risk_analysis"]): create_async_hotkey_handler(
                hotkey_handlers.personal_risk_analysis
            ),
            str(TRIGGER_FILES["export_range_context"]): create_async_hotkey_handler(
                hotkey_handlers.export_context_by_range
            ),
            # --- Data Mappings ---
            str(TRIGGER_FILES["save_input"]): create_async_hotkey_handler(
                hotkey_handlers.save_input
            ),
            str(TRIGGER_FILES["save_output"]): create_async_hotkey_handler(
                hotkey_handlers.save_output
            ),

            # --- ADD THIS NEW MAPPING BLOCK ---
            str(TRIGGER_FILES["save_thought_process"]): create_async_hotkey_handler(
                hotkey_handlers.save_thought_process
            ),
            # ------------------------------------
            str(TRIGGER_FILES["cancel_turn"]): hotkey_handlers.cancel_last_turn,
            str(TRIGGER_FILES["mark_high_quality"]): hotkey_handlers.mark_as_high_quality,
            # --- Audio Mappings ---
            str(TRIGGER_FILES["read_aloud"]): create_async_hotkey_handler(
                hotkey_handlers.read_text_aloud
            ),
            str(TRIGGER_FILES["toggle_read_aloud"]): hotkey_handlers.toggle_read_aloud_mode,
            str(TRIGGER_FILES["voice_to_text"]): hotkey_handlers.voice_to_text_workflow,
            str(TRIGGER_FILES["meeting_mode"]): hotkey_handlers.toggle_meeting_mode,
            # --- Advanced Search Mappings ---
            str(TRIGGER_FILES["codebase_search"]): create_async_hotkey_handler(
                hotkey_handlers.search_codebase
            ),
            str(TRIGGER_FILES["personal_memory_advisor"]): create_async_hotkey_handler(
                hotkey_handlers.analyze_personal_history
            ),
            str(TRIGGER_FILES["talent_pool_search"]): create_async_hotkey_handler(
                hotkey_handlers.find_and_search_talent_pools
            ),
            str(TRIGGER_FILES["import_constitution_principle"]): create_async_hotkey_handler(
                hotkey_handlers.import_constitution_principle
            ),
            str(TRIGGER_FILES["phrase_expander"]): create_async_hotkey_handler(
                hotkey_handlers.expand_phrase
            ),
            
            # ==============================================================================
            #      【【【 THIS IS THE NEW LINE FOR OUR POWER SEARCH FEATURE 】】】
            # ==============================================================================
            str(TRIGGER_FILES["power_search_and_answer"]): create_async_hotkey_handler(
                hotkey_handlers.power_search_and_answer
            ),
            str(TRIGGER_FILES["add_phrase"]): create_async_hotkey_handler(
                hotkey_handlers.add_phrase
            ),
            str(TRIGGER_FILES["add_full_content"]): create_async_hotkey_handler(
                hotkey_handlers.add_full_content
            ),
            str(TRIGGER_FILES["delete_phrase_mapping"]): create_async_hotkey_handler(
                hotkey_handlers.delete_phrase_mapping
            ),
            # --- ADD THIS NEW MAPPING ---
            str(TRIGGER_FILES["base64_conversion"]): create_async_hotkey_handler(
                hotkey_handlers.convert_to_base64
            ),

        }
        print(">> [Async System] Hotkey file watcher initialized.")

    def on_created(self, event):
        if not event.is_directory and event.src_path in self.function_map:
            print(f"\n>> [Async Signal] Received task: {Path(event.src_path).name}")
            asyncio.run_coroutine_threadsafe(
                self._handle_event(event.src_path), self.loop
            )

    async def _handle_event(self, src_path):
        try:
            handler = self.function_map.get(src_path)
            if not handler: return
            if asyncio.iscoroutinefunction(handler):
                await handler()
            elif callable(handler):
                await asyncio.to_thread(handler)
            if os.path.exists(src_path):
                os.unlink(src_path)
        except Exception as e:
            print(f"❌ {Colors.RED}[Handler Error] An error occurred while processing task for {Path(src_path).name}:{Colors.ENDC}")
            traceback.print_exc()
# ==============================================================================
#      【【【 3. REPLACE your `async def main()` and `if __name__` block with this FINAL, COMPLETE version 】】】
# ==============================================================================

def create_async_hotkey_handler(target_func, *args):
    """
    A wrapper that retrieves selected text and then calls the async target function.
    [CORRECTED] - Now correctly handles both async and sync target functions.
    """
    async def handler():
        # This is a synchronous, blocking function. We run it in a thread.
        def _get_text():
            text = ""
            try:
                text = subprocess.run(["xclip", "-o", "-selection", "primary"], capture_output=True, text=True, check=True).stdout
            except Exception:
                try:
                    text = subprocess.run(["wl-paste", "-p"], capture_output=True, text=True, check=True).stdout
                except Exception:
                    text = pyperclip.paste()
            return text.strip()

        text_to_process = await asyncio.to_thread(_get_text)

        if text_to_process:
            # This logic now correctly handles both async and sync functions from the map.
            if asyncio.iscoroutinefunction(target_func):
                # If the target is already async, just call it.
                await target_func(text_to_process, *args)
            else:
                # If the target is a regular sync function, run it in a thread.
                await asyncio.to_thread(target_func, text_to_process, *args)
        else:
            # [FIX] Added 'await' before the async safe_notification call.
            await safe_notification("No Text Found", "Please select or copy text first.")

    return handler






async def main():
    """The main asynchronous entry point for the entire application."""
    # 1. Initial Setup
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 70)
    print("      AI Core v8.0 - High-Performance Asynchronous Edition")
    print("=" * 70)

    if not WATCHDOG_AVAILABLE:
        sys.exit(1)
    # ==============================================================================
    #      【【【 在这里添加下面这一行，用于启动时导出 】】】
    # ==============================================================================
    system_services.export_all_databases_to_markdown()
    # ==============================================================================
    # 2. Start Core Services Concurrently for maximum speed
    print(">> [Async Main] Initializing all core services in parallel...")
    init_tasks = [
        ai_services.setup_api(),
        database_manager.setup_all_databases(),
        ai_services.setup_embedding_model(),
        audio_services.setup_whisper_model()
    ]
    results = await asyncio.gather(*init_tasks, return_exceptions=True)

    # Check for any failures during the critical startup phase
    if not all(results) or any(isinstance(r, Exception) for r in results):
        print(f"❌ {Colors.RED}A critical service failed to start. Exiting.{Colors.ENDC}")
        sys.exit(1)

    # 3. Run Startup Maintenance (already async)
    await system_services.run_startup_maintenance()

    # 4. Start the dedicated SYNCHRONOUS background thread for audio processing
    print(">> [Async Main] Starting background transcription processor thread...")
    threading.Thread(target=audio_services.processor_task, daemon=True).start()
    print("✅ [System] Background processor is running.")



    # 5. Setup IPC Directory for Hotkeys
    settings.IPC_DIR.mkdir(exist_ok=True)
    for file_path in TRIGGER_FILES.values():
        if file_path.exists():
            file_path.unlink()

    # 6. Start the File Watcher
    loop = asyncio.get_running_loop()
    state.main_loop = loop # <-- ADD THIS LINE
    observer = Observer()
    observer.schedule(AsyncFileTriggerHandler(loop), str(settings.IPC_DIR), recursive=False)
    observer.start()
    print("✅ [System] Core services are running. Listening for hotkey signals...")
    
    # 7. Display User Instructions (THIS BLOCK IS NOW FULLY RESTORED)
    # ========================================================================
    #      【【【 THIS IS THE RESTORED PRINT BLOCK 】】】
    # ========================================================================
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
# --- ADD THIS NEW LINE TO THE PRINT INSTRUCTIONS ---
    print(f"  - [Win+Q] -> Imports selected text as a {Colors.BLUE}new Core Principle{Colors.ENDC}")
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
 # --- ADD THIS NEW LINE ---
    print(f"  - [Win+E] -> {Colors.MAGENTA}Power Search:{Colors.ENDC} Solves a problem using Google Search + LLM")
    print(f"  - [Win+Z] -> {Colors.CYAN}Saves new Phrase Shortcut{Colors.ENDC}")
    print(f"  - [Win+X] -> {Colors.CYAN}Adds Full Content to the pending shortcut{Colors.ENDC}")
    print(f"  - [Win+C] -> {Colors.YELLOW}Deletes{Colors.ENDC} an existing phrase mapping by its shortcut")
    # --- ADD THIS NEW LINE ---
    print(f"  - [Win+B] -> {Colors.MAGENTA}Base64:{Colors.ENDC} Auto Encodes/Decodes selected text")
    # ==============================================================================
    #      【【【 END OF ADDITION 】】】
    # ==============================================================================

    print("\n  Press Ctrl+C to safely exit the program.")
    print("=" * 70 + "\n")
    # ========================================================================
    #      【【【 END OF RESTORED BLOCK 】】】
    # ========================================================================

    # 8. Keep the Application Alive
    try:
        # This will keep the main async task alive indefinitely.
        # Other tasks (like the watchdog handler) will run in the background.
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        print("\n>> [Async Main] Main task cancelled, shutting down.")
    finally:
        observer.stop()
        observer.join()
        print(">> [System] Exited safely.")


if __name__ == "__main__":
    # ==============================================================================
    #      【【【 用下面这个增强版替换您原来的 if __name__ ... 代码块 】】】
    # ==============================================================================
    try:
        # This is the new entry point that starts the asyncio event loop.
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n>> [System] Shutdown signal (Ctrl+C) received. Exiting gracefully.")
    finally:
        # 这个 finally 块确保无论程序如何退出，都会执行最后的导出操作
        print(">> [System] Performing final database export to Markdown before closing...")
        system_services.export_all_databases_to_markdown()
        print(">> [System] Exited safely.")
    # ==============================================================================
