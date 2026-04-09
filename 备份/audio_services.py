# core/audio_services.py

import os
import sqlite3
import subprocess
import tempfile
import threading
import traceback
from pathlib import Path

import pyperclip
from faster_whisper import WhisperModel

# Import our custom modules
import config
from core import state
from utils.helpers import Colors, is_primarily_chinese, get_local_time_str, safe_notification

def setup_whisper_model():
    """Loads the faster-whisper model from a local project folder."""
    try:
        local_model_path = "./faster-whisper-large-v3-local"

        if not os.path.isdir(local_model_path):
            print(f"❌ {Colors.RED}[Whisper Error] Model folder not found at '{local_model_path}'!{Colors.ENDC}")
            print(f"   {Colors.YELLOW}Please ensure you have downloaded the model files there.{Colors.ENDC}")
            return False

        print(f">> [Audio Service] Loading Whisper model from local path: {local_model_path}")
        state.WHISPER_MODEL = WhisperModel(local_model_path, device="cpu", compute_type="int8")
        print(f"✅ {Colors.GREEN}[Audio Service] Whisper model loaded successfully.{Colors.ENDC}")
        return True

    except Exception as e:
        print(f"❌ {Colors.RED}[Whisper Error] Failed to load local model: {e}{Colors.ENDC}")
        return False

def piper_tts_task(text: str):
    """
    The core TTS function that generates and plays audio using the Piper executable.
    This function is designed to be run in a background thread.
    It uses stdin to pass text, which is more robust than writing to a temp file.
    """
    global tts_process
    temp_audio_file = None
    try:
        print(f"\n{Colors.BLUE}[Audio Service] Generating TTS audio for text (length: {len(text)})...{Colors.ENDC}")

        # Assuming the script is run from the project root
        script_dir = Path("./")
        piper_exe = script_dir / "piper" / "piper"

        # Auto-detect language and select the appropriate voice model
        if is_primarily_chinese(text):
            model_file = script_dir / "zh_CN-huayan-medium.onnx"
            config_file = script_dir / "zh_CN-huayan-medium.onnx.json"
            print("   -> Using Chinese TTS model.")
        else:
            model_file = script_dir / "en_US-lessac-medium.onnx"
            config_file = script_dir / "en_US-lessac-medium.onnx.json"
            print("   -> Using English TTS model.")

        # Create a temporary file just for the audio output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fp_audio:
            temp_audio_file = fp_audio.name

        # Command to run Piper. It reads from stdin by default.
        piper_command = [
            str(piper_exe),
            "--model", str(model_file),
            "--config", str(config_file),
            "--output_file", temp_audio_file,
        ]

        print("   -> Executing Piper command via STDIN...")
        # Run the command, piping the text directly to the process's standard input.
        subprocess.run(
            piper_command,
            check=True,
            capture_output=True, # Capture stderr for debugging
            input=text.encode("utf-8"), # This is the key fix
            timeout=180,
        )

        print("   -> Audio generated. Starting playback...")
        # Play the generated audio file using aplay
        state.tts_process = subprocess.Popen(["aplay", temp_audio_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        state.tts_process.wait() # Wait for playback to finish
        print(f"   -> {Colors.GREEN}Playback complete.{Colors.ENDC}")

    except subprocess.TimeoutExpired:
        print(f"   -> {Colors.RED}TTS process timed out. The text may be too long.{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"   -> {Colors.RED}Piper executable failed! Error:{Colors.ENDC}")
        print(f"   -> {Colors.YELLOW}STDERR: {e.stderr.decode('utf-8', errors='ignore')}{Colors.ENDC}")
    except Exception as e:
        print(f"   -> {Colors.RED}An unexpected error occurred during TTS: {e}{Colors.ENDC}")
        traceback.print_exc()
    finally:
        # Cleanup
        if temp_audio_file and os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        state.tts_process = None

# In core/audio_services.py
# REPLACE the entire processor_task function with this CORRECTED version:

def processor_task():
    """
    An infinite loop that runs in a background thread. It waits for audio file paths
    to appear in the transcription_queue, processes them, and saves the result.
    [CORRECTED VERSION] - Does not interact with the app lock.
    """
    while True:
        try:
            audio_path_str = state.transcription_queue.get()

            print(f"\n{Colors.BLUE}>> [Audio Processor] Picked up new task: {Path(audio_path_str).name}{Colors.ENDC}")
            safe_notification("New Transcription", "Processing audio chunk...")

            segments, info = state.WHISPER_MODEL.transcribe(audio_path_str)
            full_text = " ".join(segment.text for segment in segments).strip()

            if full_text:
                is_meeting_chunk = Path(audio_path_str).name.startswith("rec_")
                prefix = "[Meeting] " if is_meeting_chunk else ""
                final_text = f"{prefix}{full_text}"

                print(f"   -> [Processor] Transcription complete (Lang: {info.language}). Saving to DB.")
                with sqlite3.connect(config.VOICE_TRANSCRIPTS_DB) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"INSERT INTO {config.VOICE_TRANSCRIPTS_TABLE_NAME} (timestamp, language_detected, transcribed_text) VALUES (?, ?, ?)",
                        (get_local_time_str(), info.language, final_text),
                    )
                print(f"   -> [Processor] ✅ Transcript saved to database.{Colors.ENDC}")
                
                if not is_meeting_chunk:
                     pyperclip.copy(full_text)
                     safe_notification("Transcription Complete", "Text copied to clipboard.")
                     print(f"   -> {Colors.GREEN}[Clipboard] ✅ Transcribed text copied!{Colors.ENDC}")
            else:
                print(f"   -> [Processor] {Colors.YELLOW}No speech detected in this chunk.{Colors.ENDC}")

            # REMOVED: The block that released the app_controller_lock is now gone.

            if not config.KEEP_AUDIO_FILES and os.path.exists(audio_path_str):
                os.unlink(audio_path_str)

            state.transcription_queue.task_done()
        except Exception as e:
            print(f"❌ {Colors.RED}[Audio Processor Error] A critical error occurred: {e}{Colors.ENDC}")
            traceback.print_exc()
