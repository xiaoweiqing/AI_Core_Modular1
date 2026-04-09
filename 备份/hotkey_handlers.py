# ==============================================================================
#      【【【 1. REPLACE your entire import block with this one 】】】
# ==============================================================================
import aiosqlite
import uuid
import pyperclip
import asyncio      # The core async library
import aiosqlite    # The async replacement for sqlite3
import json
import uuid
import traceback
import re
import time
from pathlib import Path
from typing import Optional
import numpy as np
import sounddevice as sd
import soundfile as sf
from qdrant_client import models
# At the top of core/hotkey_handlers.py
from core import database_manager # Import the entire module
# Import our custom modules
from config import settings
from core import state
from core import ai_services
from core import audio_services
from utils.helpers import Colors, safe_notification, clean_text, get_local_time_str

try:
    import fast_grep_engine
except ImportError:
    print(f"{Colors.RED}Warning: 'fast_grep_engine' not found. Codebase search (Alt+K) will be disabled.{Colors.ENDC}")
    fast_grep_engine = None

# ==============================================================================
#      【【【 2. REPLACE all functions in the file with these async versions 】】】
# ==============================================================================

# --- AI-Powered Translation & Prompting Workflows ---

# In core/hotkey_handlers.py
# REPLACE the first four functions in the file with this corrected block.

async def translate_to_en(text: str):
    """[ASYNC] Handles Alt+Q: Translates text to English and logs it to the database."""
    if state.app_controller_lock.locked():
        await safe_notification("System Busy", "Another operation is in progress.")
        return
    async with state.app_controller_lock:
        action_log = "[Async Translate & Read]" if state.READ_ALOUD_MODE_ENABLED else "[Async Translate]"
        print(f"\n{Colors.BLUE}{action_log} Translating to English...{Colors.ENDC}")
        
        final_text = await ai_services.run_ai_task(
            f"Translate the following text to fluent, natural-sounding English. Preserve code blocks. Output only the translated text:\n\n{clean_text(text)}"
        )

        if not final_text:
            await safe_notification("Translation Failed", "AI model did not return a response.")
            return

        await asyncio.to_thread(pyperclip.copy, final_text)
        await safe_notification("Translation Complete", "Result copied to clipboard.")
        print(f"{Colors.YELLOW}--- [ Translation Complete | Copied ] ---{Colors.ENDC}")
        print(f"{Colors.CYAN}{final_text}{Colors.ENDC}")

        # --- THIS IS THE NEW PART ---
        # Start the database logging as a background task
        print("   -> [Async Task] Submitting translation to daily log DB...")
        asyncio.create_task(database_manager.log_daily_record("TRANSLATE", text, final_text))
        # --- END OF NEW PART ---
        
        if state.READ_ALOUD_MODE_ENABLED:
            print("   -> Read Aloud mode is ON, starting background TTS task...")
            asyncio.create_task(read_text_aloud(final_text))


async def translate_to_zh(text: str):
    """[ASYNC] Handles Alt+W: Translates text to Chinese and logs it to the database."""
    if state.app_controller_lock.locked():
        await safe_notification("System Busy", "Another operation is in progress.")
        return
    async with state.app_controller_lock:
        action_log = "[Async Translate & Read]" if state.READ_ALOUD_MODE_ENABLED else "[Async Translate]"
        print(f"\n{Colors.BLUE}{action_log} Translating to Chinese...{Colors.ENDC}")

        final_text = await ai_services.run_ai_task(
            f"将以下文本翻译成流畅、自然的中文。保留代码块。只输出翻译后的文本:\n\n{clean_text(text)}"
        )

        if not final_text:
            await safe_notification("Translation Failed", "AI model did not return a response.")
            return

        await asyncio.to_thread(pyperclip.copy, final_text)
        await safe_notification("Translation Complete", "Result copied to clipboard.")
        print(f"{Colors.YELLOW}--- [ Translation Complete | Copied ] ---{Colors.ENDC}")
        print(f"{Colors.GREEN}{final_text}{Colors.ENDC}")

        # --- THIS IS THE NEW PART ---
        # Start the database logging as a background task
        print("   -> [Async Task] Submitting translation to daily log DB...")
        asyncio.create_task(database_manager.log_daily_record("TRANSLATE", text, final_text))
        # --- END OF NEW PART ---

        if state.READ_ALOUD_MODE_ENABLED:
            print("   -> Read Aloud mode is ON, starting background TTS task...")
            asyncio.create_task(read_text_aloud(final_text))

# In core/hotkey_handlers.py
# REPLACE the optimize_prompt function with this version, guided by the user.

async def optimize_prompt(text: str):
    """
    [ASYNC] Handles Alt+E: Transforms text into a formal AI instruction and logs it.
    """
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        print(f"\n{Colors.BLUE}[Async Handler] Formalizing text into bilingual AI instructions...{Colors.ENDC}")

        meta_prompt = f"""
# ROLE
You are an AI Instruction Formalization Engine, fluent in both English and Chinese.
# TASK
Your sole purpose is to convert the user-provided text into two versions of a highly formal, objective, and explicit AI instruction: one in English and one in Chinese. You must adhere to the following rules with absolute strictness for BOTH language outputs:
1.  ABSOLUTE FIDELITY: The original meaning, intent, and all specific details of the source text must be preserved exactly. You are forbidden from adding, removing, or altering any factual content or core concepts.
2.  FORMAL STRUCTURE: Rephrase the text as a direct, unambiguous command. The output must be structured as a clear, actionable directive.
3.  OBJECTIVE LANGUAGE: Eliminate all colloquialisms, conversational filler, and ambiguity. Replace them with precise, formal, and objective language.
4.  SELF-CONTAINMENT: Your transformation must be based *only* on the provided source text.
# OUTPUT FORMAT
You MUST output a single, valid JSON object and nothing else. The JSON object must contain two keys:
- "en_instruction": The formalized instruction in English.
- "zh_instruction": The formalized instruction in Chinese.
Example format: {{"en_instruction": "...", "zh_instruction": "..."}}
# SOURCE TEXT
---
{text}
---
# OUTPUT
Generate only the JSON object containing the two formalized instructions.
"""
        ai_response_json = await ai_services.run_ai_task(meta_prompt)

        if not ai_response_json:
            await safe_notification("Formalization Failed", "AI model did not return a response.")
            return

        try:
            instructions = json.loads(ai_response_json)
            en_instruction = instructions.get("en_instruction", "Error: English version not found.")
            zh_instruction = instructions.get("zh_instruction", "错误：未找到中文版本。")

            await asyncio.to_thread(pyperclip.copy, en_instruction)
            await safe_notification("Instruction Formalized", "English version copied to clipboard.")

            print(f"{Colors.YELLOW}--- [ AI Instruction (EN) | Copied to Clipboard ] ---{Colors.ENDC}")
            print(f"{Colors.GREEN}{en_instruction}{Colors.ENDC}")
            print(f"{Colors.YELLOW}--- [ AI 指令 (ZH) | Display Only ] ---{Colors.ENDC}")
            print(f"{Colors.CYAN}{zh_instruction}{Colors.ENDC}")

            # --- THIS IS THE NEW PART ---
            # Start the database logging as a background task
            print("   -> [Async Task] Submitting optimization to daily log DB...")
            asyncio.create_task(database_manager.log_daily_record("OPTIMIZE_PROMPT", text, en_instruction, meta_prompt))
            # --- END OF NEW PART ---

        except json.JSONDecodeError:
            await safe_notification("Formalization Failed", "AI returned an invalid format. See console.")
            print(f"❌ {Colors.RED}[Error] Failed to parse AI response. The model did not return valid JSON.{Colors.ENDC}")
            print(f"   Raw AI Response: {ai_response_json}")

async def get_concise_answer(text: str):
    """[ASYNC] Handles Alt+N: Gets a hyper-concise answer."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        print(f"\n{Colors.BLUE}[Async Handler] Requesting concise answer...{Colors.ENDC}")
        prompt = f"""...""" # Your prompt text here
        ai_response = await ai_services.run_ai_task(prompt)
        if not ai_response:
            # [FIX] Added await
            await safe_notification("AI Error", "The model did not return a response.")
            return

        await asyncio.to_thread(pyperclip.copy, ai_response)
        # [FIX] Added await
        await safe_notification("Answer Ready", "Concise answer copied to clipboard.")
        print(f"{Colors.YELLOW}--- [ Concise Answer | Copied ] ---{Colors.ENDC}")
        print(f"{Colors.GREEN}{ai_response}{Colors.ENDC}")

# In core/hotkey_handlers.py
# REPLACE the existing personal_risk_analysis function.

# In core/hotkey_handlers.py
# REPLACE the existing personal_risk_analysis function.

# ==============================================================================
#      【【【 这是针对 Alt+Z 功能的精准修复 】】】
# ==============================================================================
async def _save_risk_analysis_to_sqlite_async(situation: str, ai_response: str):
    """[ASYNC BG TASK] Saves a completed risk analysis to the SQLite database."""
    print("   -> [Async BG Task] Saving risk analysis to SQLite...")
    try:
        async with aiosqlite.connect(str(settings.RISK_ASSESSMENT_DB)) as conn:
            await conn.execute(
                f"INSERT INTO {settings.RISK_ASSESSMENT_TABLE_NAME} (timestamp, input_situation, ai_full_response) VALUES (?, ?, ?)",
                (get_local_time_str(), situation, ai_response),
            )
            await conn.commit()
        print(f"✅ {Colors.GREEN}[Async SQLite] Risk analysis record saved successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"❌ {Colors.RED}[Async SQLite Error] Failed to save risk analysis: {e}{Colors.ENDC}")
        traceback.print_exc()


async def _save_risk_analysis_to_vector_db_async(situation: str, ai_response: str):
    """[ASYNC BG TASK] Vectorizes and saves a risk analysis to the Qdrant history collection."""
    print("   -> [Async BG Task] Saving risk analysis to Vector DB...")
    try:
        # We combine the situation and response to create a rich, searchable document
        full_text = f"### Situation Analyzed:\n{situation}\n\n### AI-Generated Analysis:\n{ai_response}"
        
        vector = await ai_services.generate_text_vector(full_text)
        if not vector:
            print(f"❌ {Colors.RED}[Async Vector Error] Vectorization failed for risk analysis.{Colors.ENDC}")
            return

        point_id = str(uuid.uuid4())
        payload = {
            "timestamp": get_local_time_str(),
            "original_situation": situation,
            "full_analysis_text": full_text,
        }
        
        await asyncio.to_thread(
            state.QDRANT_CLIENT.upsert,
            collection_name=settings.QDRANT_RISK_ANALYSIS_COLLECTION,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
            wait=True,
        )
        print(f"✅ {Colors.GREEN}[Async Vector DB] Risk analysis vectorized and indexed successfully.{Colors.ENDC}")
    except Exception as e:
        print(f"❌ {Colors.RED}[Async Vector Error] Failed to index risk analysis: {e}{Colors.ENDC}")
        traceback.print_exc()


async def personal_risk_analysis(text: str):
    """
    [ASYNC] Handles Alt+Z: The complete closed-loop risk analysis workflow.
    1. Analyzes text against core principles.
    2. Displays the result to the user.
    3. Saves the result to BOTH the SQLite archive and the Vector DB history in the background.
    """
    if not state.IS_QDRANT_DB_READY:
        await safe_notification("Error", "Vector Database is not ready.")
        return
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        print(f"\n{Colors.MAGENTA}[Async Handler] Initiating Closed-Loop Risk Analysis...{Colors.ENDC}")
        
        # === Step 1: Perform the Analysis (This part is mostly unchanged) ===
        query_vector = await ai_services.generate_text_vector(text)
        if not query_vector:
            await safe_notification("Vectorization Failed", "Could not generate vector.")
            return

        search_results = await asyncio.to_thread(
            state.QDRANT_CLIENT.query_points,
            collection_name="personal_constitution", # We still query the constitution
            query=query_vector,
            limit=3
        )
        
        retrieved_principles = ""
        for result in search_results.points:
            retrieved_principles += f"--- [Relevant Core Principle] ---\n{result.payload.get('text_chunk', '')}\n\n"

        if not retrieved_principles:
             await safe_notification("Analysis Error", "Could not find any relevant principles.")
             return

        # NEW: We now also search our past analysis history to see if we've encountered this before.
        history_search_results = await asyncio.to_thread(
            state.QDRANT_CLIENT.query_points,
            collection_name=settings.QDRANT_RISK_ANALYSIS_COLLECTION,
            query=query_vector,
            limit=2
        )
        retrieved_history = ""
        if history_search_results.points:
            for result in history_search_results.points:
                retrieved_history += f"--- [Relevant Past Analysis] ---\n{result.payload.get('full_analysis_text', '')}\n\n"

        prompt = f"""
# Your Role
You are my AI strategic advisor. Your primary function is to provide a holistic and practical analysis that integrates my core principles with general knowledge and common sense.

# My Personal Constitution (The Primary Strategic Filter)
This is the most important context. Your analysis must be fundamentally aligned with these principles, but not blindly constrained by them.
---
{retrieved_principles}
---

# Relevant Past Analyses (If any)
Use these for context and to ensure consistency in your reasoning.
---
{retrieved_history}
---

# New Situation to Analyze
"{text}"

# Your Core Task
Provide a "Strategic Briefing" on the new situation. Do not be a simple rule-checker. **Synthesize** my principles with your own broad knowledge of the world, business, and human psychology to provide the most insightful and actionable advice possible. Your response must be both principled and practical.

# Required Output Structure:
1.  **Executive Summary:** A brief, top-level verdict. Does this align or conflict with my mission?
2.  **Principled Risk Assessment:** Analyze the risks through the lens of my constitution.
3.  **Common Sense Risk Assessment:** What are the obvious, real-world risks that anyone should consider, even without my constitution?
4.  **Opportunity Analysis:** Identify principle-aligned opportunities for growth.
5.  **Final Actionable Advice:** Provide a clear, synthesized recommendation that balances my principles with practical reality.
"""
        analysis_response = await ai_services.run_ai_task(prompt)
        if not analysis_response:
            await safe_notification("Analysis Failed", "AI model did not return a response.")
            return

        # === Step 2: Display Results Immediately to the User ===
        await asyncio.to_thread(pyperclip.copy, analysis_response)
        await safe_notification("Analysis Complete", "Results copied. Saving to DBs in background.")
        print(f"{Colors.YELLOW}--- [ Personal Constitution Analysis | Copied ] ---{Colors.ENDC}")
        print(f"{Colors.CYAN}{analysis_response}{Colors.ENDC}")

        # === Step 3: Start the Background Saving Tasks (Fire and Forget) ===
        print(f"{Colors.BLUE}--- [Async Tasks] Dispatching save operations to background... ---{Colors.ENDC}")
        asyncio.create_task(_save_risk_analysis_to_sqlite_async(text, analysis_response))
        asyncio.create_task(_save_risk_analysis_to_vector_db_async(text, analysis_response))

# ==============================================================================
#      【【【 END OF REPLACEMENT BLOCK 】】】
# ==============================================================================
# ==============================================================================
#      【【【 修复结束 】】】
# ==============================================================================

# --- Data Recording Workflows ---

# In core/hotkey_handlers.py
# REPLACE the entire block of four data recording functions.

async def save_input(text: str):
    """[ASYNC] Handles Alt+S: Saves the user's input as a new, pending record."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        if state.last_record_id is not None:
            await safe_notification("Action Blocked", f"Input (ID: {state.last_record_id}) is pending.")
            return

        print(f"\n{Colors.MAGENTA}[Async Handler] Capturing new input record...{Colors.ENDC}")
        metadata_json = json.dumps({"created_at": get_local_time_str()})
        
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            cursor = await conn.execute(
                f"INSERT INTO {settings.CORPUS_TABLE_NAME} (input_text, metadata, status) VALUES (?, ?, ?)",
                (text, metadata_json, "pending_output"),
            )
            await conn.commit()
            state.last_record_id = cursor.lastrowid

        print(f"✅ {Colors.GREEN}[Async SQLite] Input saved as ID: {state.last_record_id}.{Colors.ENDC}")
        await safe_notification("Input Saved", f"Record ID: {state.last_record_id} is pending.")
        
        print(f"   -> [Async Task] Submitting metadata task for record {state.last_record_id}.")
        asyncio.create_task(process_metadata_and_vectorize(state.last_record_id, "input"))


async def save_output(text: str):
    """[ASYNC] Handles Alt+D: Pairs the AI's output with the pending input record."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        if state.last_record_id is None:
            await safe_notification("Action Blocked", "No input pending. Use Alt+S first.")
            return

        record_id_to_process = state.last_record_id
        print(f"\n{Colors.MAGENTA}[Async Handler] Pairing output with record ID: {record_id_to_process}...{Colors.ENDC}")
        
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            await conn.execute(
                f"UPDATE {settings.CORPUS_TABLE_NAME} SET output_text = ?, status = ? WHERE id = ?",
                (text, "pending_summaries", record_id_to_process),
            )
            await conn.commit()

        state.last_completed_id = record_id_to_process
        state.last_record_id = None

        print(f"✅ {Colors.GREEN}[Async SQLite] Record {record_id_to_process} is complete.{Colors.ENDC}")
        await safe_notification("Output Saved", f"Record {record_id_to_process} completed!")
        
        print(f"   -> [Async Task] Submitting full processing task for record {record_id_to_process}.")
        asyncio.create_task(process_metadata_and_vectorize(record_id_to_process, "output"))


async def cancel_last_turn():
    """[ASYNC] Handles Alt+C: Deletes the last pending input record."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        if state.last_record_id is None:
            await safe_notification("Cancel Failed", "No pending input to cancel.")
            return

        record_id_to_delete = state.last_record_id
        state.last_record_id = None
        
        print(f"\n{Colors.YELLOW}[Async Handler] Deleting pending record ID: {record_id_to_delete}...{Colors.ENDC}")
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            await conn.execute(f"DELETE FROM {settings.CORPUS_TABLE_NAME} WHERE id = ?", (record_id_to_delete,))
            await conn.commit()
        
        print(f"✅ {Colors.GREEN}[Async SQLite] Deleted pending record ID: {record_id_to_delete}.{Colors.ENDC}")
        await safe_notification("Action Canceled", f"Deleted pending record ID: {record_id_to_delete}.")


async def mark_as_high_quality():
    """[ASYNC] Handles Alt+F: Marks the most recently completed pair as 'high-quality'."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        if state.last_completed_id is None:
            await safe_notification("Annotation Failed", "No recently completed record to mark.")
            return

        record_id_to_mark = state.last_completed_id
        state.last_completed_id = None
        
        print(f"\n{Colors.BLUE}[Async Handler] Marking record ID: {record_id_to_mark} as 'high-quality'...{Colors.ENDC}")
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            await conn.execute(
                f"UPDATE {settings.CORPUS_TABLE_NAME} SET quality_label = ? WHERE id = ?",
                ("high-quality", record_id_to_mark),
            )
            await conn.commit()

        print(f"✅ {Colors.GREEN}[Async SQLite] Record {record_id_to_mark} marked as high-quality.{Colors.ENDC}")
        await safe_notification("Annotation Successful", f"Record {record_id_to_mark} marked.")

# --- Asynchronous Backend Processing ---

# In core/hotkey_handlers.py
# REPLACE the existing process_metadata_and_vectorize function with this block.

async def process_metadata_and_vectorize(record_id: int, stage: str):
    """[ASYNC BG TASK] Fetches a record, generates summaries, and indexes it in Qdrant."""
    print(f">> [Async BG] Starting job for record {record_id} (Stage: {stage})")
    try:
        # [FIX] Use 'settings' object and str() for the path
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            cursor = await conn.execute(
                # [FIX] Use 'settings' object
                f"SELECT input_text, output_text, metadata FROM {settings.CORPUS_TABLE_NAME} WHERE id = ?", (record_id,)
            )
            record = await cursor.fetchone()
        
        if not record: return
        input_text, output_text, metadata_json = record
        metadata = json.loads(metadata_json)

        text_to_summarize = ""
        if stage == "input":
            print(f"   -> Record {record_id}: Summarizing input...")
            text_to_summarize = input_text
        elif stage == "output" and output_text:
            print(f"   -> Record {record_id}: Summarizing output...")
            text_to_summarize = output_text

        if text_to_summarize:
            summary = await ai_services.run_ai_task(f"Summarize the following in one short sentence:\n\n{clean_text(text_to_summarize)}")
            if summary:
                metadata[f"{stage}_summary"] = summary
        
        # [FIX] Use 'settings' object and str() for the path
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            await conn.execute(
                # [FIX] Use 'settings' object
                f"UPDATE {settings.CORPUS_TABLE_NAME} SET metadata = ? WHERE id = ?",
                (json.dumps(metadata, ensure_ascii=False), record_id),
            )
            await conn.commit()

        if output_text and state.IS_QDRANT_DB_READY:
            print(f"   -> Record {record_id}: Vectorizing complete record...")
            full_text = f"User Input: {input_text}\n\nAI Response: {output_text}"
            
            # [FIX] Added 'await' before async function call
            vector = await ai_services.generate_text_vector(full_text)
            
            if not vector:
                print(f"❌ {Colors.RED}[Async BG Error] Vectorization failed for record {record_id}.{Colors.ENDC}")
                return

            payload = {"source_id": record_id, "full_turn": full_text, **metadata}
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(record_id)))
            
            await asyncio.to_thread(
                state.QDRANT_CLIENT.upsert,
                # [FIX] Use 'settings' object
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
                wait=True,
            )
            
            # [FIX] Use 'settings' object and str() for the path
            async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
                await conn.execute(
                    # [FIX] Use 'settings' object
                    f"UPDATE {settings.CORPUS_TABLE_NAME} SET status = ? WHERE id = ?", ("complete", record_id)
                )
                await conn.commit()
            
            print(f"✅ {Colors.GREEN}[Async BG Complete] Successfully indexed record ID: {record_id}!{Colors.ENDC}")

    except Exception as e:
        print(f"❌ {Colors.RED}[Async BG Error] Processing failed for record {record_id}: {e}{Colors.ENDC}")
        traceback.print_exc()

# --- Text-to-Speech (TTS) Workflows ---

async def read_text_aloud(text: str):
    """[ASYNC] Handles Alt+R: Asynchronously starts or stops TTS playback."""
    if state.tts_process and state.tts_process.poll() is None:
        print(f"\n{Colors.YELLOW}[TTS Stop] Terminating active playback...{Colors.ENDC}")
        await asyncio.to_thread(state.tts_process.terminate)
        state.tts_process = None
        return
    # This calls an async wrapper in audio_services
    await audio_services.piper_tts_task(text)

# In core/hotkey_handlers.py
# REPLACE the block of functions from toggle_read_aloud_mode to the end of recorder_task.

def toggle_read_aloud_mode():
    """[SYNC] Handles Alt+T: Toggles the global read-aloud mode ON or OFF."""
    state.READ_ALOUD_MODE_ENABLED = not state.READ_ALOUD_MODE_ENABLED
    if state.READ_ALOUD_MODE_ENABLED:
        msg, color = "ON. Translations will be read aloud.", Colors.GREEN
    else:
        msg, color = "OFF. Translations will be silent.", Colors.YELLOW
    print(f"\n{color}>> [System] Read Aloud Mode is now {msg.split('.')[0]}.{Colors.ENDC}")
    
    # [FIX] Schedule the async notification to run on the main event loop
    if state.main_loop:
        asyncio.run_coroutine_threadsafe(safe_notification("Read Aloud Mode", msg), state.main_loop)

# --- Voice Recording & Transcription Workflows ---

# [SYNC-THREAD] Global variables for the synchronous audio recording stream
short_rec_stream = None
short_rec_frames = []

# [SYNC-THREAD] This function manages its own state and interacts with a dedicated audio thread.
def voice_to_text_workflow():
    """
    Handles Alt+G: A state machine to start/stop short voice recording.
    This is a SYNC function that schedules async notifications.
    """
    global short_rec_stream, short_rec_frames

    # --- Stop Recording Logic ---
    if state.IS_RECORDING:
        if not short_rec_stream:
            state.IS_RECORDING = False
            return
        try:
            short_rec_stream.stop(); short_rec_stream.close()
        except Exception as e:
            print(f"Error stopping recording stream: {e}")

        state.IS_RECORDING = False
        print(f"\n{Colors.GREEN}>> Short recording stopped. Processing in background...{Colors.ENDC}")
        # [FIX] Schedule the async notification
        if state.main_loop:
            asyncio.run_coroutine_threadsafe(safe_notification("Recording Stopped", "Processing audio..."), state.main_loop)

        if not short_rec_frames:
            print(f"   -> {Colors.YELLOW}[Warning] No audio was recorded.{Colors.ENDC}")
            return

        try:
            # [FIX] Use the settings object
            settings.AUDIO_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = get_local_time_str().replace(":", "-").replace(" ", "_")
            filename = f"short_rec_{timestamp}.wav"
            filepath = settings.AUDIO_ARCHIVE_DIR / filename
            sf.write(filepath, np.concatenate(short_rec_frames, axis=0), 16000)
            print(f"   -> {Colors.GREEN}[File Saved] Audio saved to: {filepath}{Colors.ENDC}")
            state.transcription_queue.put(str(filepath))
        except Exception as e:
            print(f"❌ {Colors.RED}[File Error] Could not save audio file: {e}{Colors.ENDC}")
        return

    # --- Start Recording Logic ---
    try:
        if state.IS_RECORDING: return
            
        state.IS_RECORDING = True
        short_rec_frames = []
        print(f"\n{Colors.YELLOW}>> Short recording started... Press Alt+G again to stop.{Colors.ENDC}")
        # [FIX] Schedule the async notification
        if state.main_loop:
            asyncio.run_coroutine_threadsafe(safe_notification("Recording Started", "Press Alt+G again to stop."), state.main_loop)
        
        def callback(indata, frames, time, status):
            short_rec_frames.append(indata.copy())
        short_rec_stream = sd.InputStream(samplerate=16000, channels=1, callback=callback)
        short_rec_stream.start()
    except Exception as e:
        print(f"❌ {Colors.RED}[Audio Error] Could not start recording: {e}{Colors.ENDC}")
        state.IS_RECORDING = False

# In core/hotkey_handlers.py

# --- Voice Recording & Transcription Workflows ---

# In core/hotkey_handlers.py
# REPLACE the existing toggle_meeting_mode and recorder_task functions with this complete block.

# ==============================================================================
#      【【【 THIS IS THE SURGICAL FIX FOR ALT+B 】】】
# ==============================================================================

# In core/hotkey_handlers.py
# REPLACE the existing toggle_meeting_mode and recorder_task functions with this complete, final block.

# ==============================================================================
#      【【【 FINAL, DEFINITIVE FIX FOR ALT+B 】】】
# ==============================================================================

# In core/hotkey_handlers.py
# REPLACE the existing meeting mode functions with this final, self-contained block.

# ==============================================================================
#      【【【 FINAL AND CORRECTED FIX FOR ALT+B 】】】
# ==============================================================================

# In core/hotkey_handlers.py
# REPLACE the existing meeting mode functions with this new, database-driven block.

# ==============================================================================
#      【【【 DATABASE-DRIVEN ALT+B FEATURE WITH AUTO-SUMMARY 】】】
# ==============================================================================

# In core/hotkey_handlers.py
# REPLACE all existing functions related to meeting mode (Alt+B) with this complete block.

# In core/hotkey_handlers.py
# REPLACE the entire block of meeting mode functions with this final version.

# ==============================================================================
#      【【【 FINAL AND CORRECTED ALT+B FEATURE BLOCK 】】】
# ==============================================================================

# In core/hotkey_handlers.py
# 用这个最终的、完整的代码块替换掉所有与会议模式相关的函数

# ==============================================================================
#      【【【 最终且正确的 ALT+B 功能代码块 】】】
# ==============================================================================

# [ASYNC] 用于异步会议录音的全局状态
meeting_rec_stream = None
meeting_rec_frames = []

def toggle_meeting_mode():
    """
    [同步调度器] 处理 Alt+B。
    - 开始：生成一个新的会话ID，并在后台启动无锁的录音任务。
    - 停止：发出停止信号，并调度有锁的总结任务。
    """
    # --- 停止逻辑 ---
    if state.MEETING_MODE_ACTIVE:
        session_id_to_process = state.current_meeting_session_id
        state.MEETING_MODE_ACTIVE = False # 向正在运行的异步任务发出停止信号
        
        print(f"\n{Colors.RED}>> [会议模式] 收到停止信号。正在生成会话 {str(session_id_to_process)[:8]} 的总结...{Colors.ENDC}")
        if state.main_loop and session_id_to_process:
            # 调度总结任务，它将在后台运行
            asyncio.run_coroutine_threadsafe(summarize_meeting_session(session_id_to_process), state.main_loop)
            asyncio.run_coroutine_threadsafe(safe_notification("会议模式", "正在停止... 稍后将生成总结。"), state.main_loop)
        return

    # --- 开始逻辑 ---
    if state.MEETING_MODE_ACTIVE: # 防止重复启动
        return
    
    try:
        state.current_meeting_session_id = str(uuid.uuid4())
        state.MEETING_MODE_ACTIVE = True
        print(f"\n{Colors.GREEN}>> [会议模式] 已开始。新会话ID: {state.current_meeting_session_id[:8]}...{Colors.ENDC}")
        if state.main_loop:
            # 调度录音任务在后台运行，它本身不会加锁
            asyncio.run_coroutine_threadsafe(recorder_task(), state.main_loop)
            asyncio.run_coroutine_threadsafe(safe_notification("会议模式已激活", "正在后台录音..."), state.main_loop)
    except Exception as e:
        print(f"❌ {Colors.RED}[会议模式错误] 无法调度任务: {e}{Colors.ENDC}")
        state.MEETING_MODE_ACTIVE = False


# In core/hotkey_handlers.py
# 用这个最终版本的函数替换掉现有的 summarize_meeting_session 函数

# ==============================================================================
#      【【【 最终版本的总结函数（已移除超时限制） 】】】
# ==============================================================================
async def summarize_meeting_session(session_id: str):
    """
    [异步工作单元] 耐心等待转写完成的信号，然后查询数据库，
    进行总结，并显示结果。
    """
    async with state.app_controller_lock:
        try:
            print(f"{Colors.BLUE}>> [会议总结] 正在等待会话 {session_id[:8]} 的最终转写（无超时限制）...{Colors.ENDC}")
            
            # 这就是关键的修复：我们移除超时，让它一直等待直到信号发出
            await state.processing_complete_event.wait()

            print(f">> [会议总结] 信号收到。正在查询数据库...{Colors.ENDC}")
            async with aiosqlite.connect(str(settings.VOICE_TRANSCRIPTS_DB)) as conn:
                cursor = await conn.execute(
                    f"SELECT transcribed_text FROM {settings.VOICE_TRANSCRIPTS_TABLE_NAME} WHERE session_id = ? ORDER BY id ASC",
                    (session_id,)
                )
                rows = await cursor.fetchall()

            if not rows:
                print(f"{Colors.YELLOW}>> [会议总结] 本次会话未检测到任何语音。{Colors.ENDC}")
                await safe_notification("会议总结", "未检测到语音。")
                return

            # 同时准备原始文本和AI总结
            full_transcript = "\n".join(row[0].replace("[Meeting] ", "") for row in rows)
            
            summary_prompt = f"""
# 角色
你是一位专业的会议助理。你的任务是分析一份原始会议记录，并生成一份清晰、结构化的总结。

# 原始会议记录
---
{full_transcript}
---

# 你的任务
根据会议记录，生成一份包含以下几点的总结：
1.  **讨论要点：** 简要概述会议讨论的核心主题。
2.  **关键决策：** 列出会议达成的明确决定。
3.  **行动项：** 列出分配给具体人员的待办事项。

如果某个部分没有相关信息，请明确指出“无”。
"""
            summary = await ai_services.run_ai_task(summary_prompt)
            if not summary:
                summary = "AI summary generation failed."

            # 将原始记录和总结合并，准备显示和复制
            final_output = (
                f"--- [ 会议原始记录 (Session: {session_id[:8]}) ] ---\
n"
                f"{full_transcript}\n\n"
                f"--- [ AI 生成的会议总结 ] ---\n"
                f"{summary}"
            )

            await asyncio.to_thread(pyperclip.copy, final_output)
            await safe_notification("会议总结已就绪", "完整记录和总结已复制到剪贴板。")
            
            print(f"\n{Colors.YELLOW}{'=' * 25} [ 会议纪要: {session_id[:8]} ] {'=' * 24}{Colors.ENDC}")
            print(f"{Colors.GREEN}{final_output}{Colors.ENDC}")
            print(f"{Colors.YELLOW}{'=' * 70}{Colors.ENDC}\n")

        except Exception as e:
            # 移除了 TimeoutError，因为我们不再有超时
            print(f"❌ {Colors.RED}[会议总结错误] 发生意外错误: {e}{Colors.ENDC}")
            traceback.print_exc()
        finally:
            state.processing_complete_event.clear()
            if state.current_meeting_session_id == session_id:
                 state.current_meeting_session_id = None
# ==============================================================================
#      【【【 修复结束 】】】
# ==============================================================================


async def recorder_task():
    """
    [异步后台任务] **这个任务不会加锁**，允许其他应用功能同时运行。
    """
    global meeting_rec_stream, meeting_rec_frames
    session_id = state.current_meeting_session_id
    
    if not session_id:
        print(f"❌ {Colors.RED}[录音错误] 无法启动，会话ID丢失。{Colors.ENDC}")
        return

    settings.AUDIO_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    meeting_rec_frames = []

    def meeting_callback(indata, frames, time, status):
        meeting_rec_frames.append(indata.copy())
    try:
        meeting_rec_stream = sd.InputStream(samplerate=16000, channels=1, callback=meeting_callback)
        meeting_rec_stream.start()
        print(f"{Colors.YELLOW}   -> [后台录音] 音频流已打开，正在录音...{Colors.ENDC}")

        while state.MEETING_MODE_ACTIVE:
            await asyncio.sleep(settings.RECORD_CHUNK_SECONDS)
            current_frames = meeting_rec_frames
            meeting_rec_frames = []
            if current_frames:
                await write_audio_chunk(current_frames, "rec_chunk", session_id)
    finally:
        if meeting_rec_stream:
            meeting_rec_stream.stop(); meeting_rec_stream.close()
        if meeting_rec_frames:
            await write_audio_chunk(meeting_rec_frames, "rec_final", session_id)
        print(f"{Colors.GREEN}>> [后台录音] 录音任务已停止并清理完毕。{Colors.ENDC}")
        # 仅当任务是由停止信号正常结束时才重置状态
        if not state.MEETING_MODE_ACTIVE:
            # This is a safety check; the main toggle handles the state change
            pass

async def write_audio_chunk(frames: list, prefix: str, session_id: Optional[str]):
    """辅助函数，现在接受一个会话ID。"""
    def _write_file():
        timestamp = get_local_time_str().replace(":", "-").replace(" ", "_")
        filename = f"{prefix}_{timestamp}.wav"
        filepath = settings.AUDIO_ARCHIVE_DIR / filename
        try:
            audio_data = np.concatenate(frames, axis=0)
            sf.write(filepath, audio_data, 16000)
            print(f"   -> {Colors.GREEN}[文件已保存] 音频已保存至: {filepath}{Colors.ENDC}")
            state.transcription_queue.put((str(filepath), session_id))
        except Exception as e:
            print(f"   -> {Colors.RED}[文件写入错误] 无法保存音频块: {e}{Colors.ENDC}")

    await asyncio.to_thread(_write_file)




# ==============================================================================
#      【【【 END OF CORRECTION 】】】
# ==============================================================================

# --- Advanced Search & Export Workflows ---

# In core/hotkey_handlers.py
# REPLACE the existing export_context_by_range function with this block.

async def export_context_by_range(range_text: str):
    """[ASYNC] Handles Alt+V: Exports dialogue history from a given ID range."""
    if state.app_controller_lock.locked(): return
    async with state.app_controller_lock:
        print(f"\n{Colors.BLUE}[Async Handler] Received export range: '{range_text}'...{Colors.ENDC}")
        match = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", range_text)
        if not match:
            # [FIX] Added 'await'
            await safe_notification("Export Failed", "Invalid format. Use 'startID-endID'.")
            return

        start_id, end_id = sorted([int(match.group(1)), int(match.group(2))])
        # [FIX] Use 'settings' object
        async with aiosqlite.connect(str(settings.CORPUS_DB)) as conn:
            cursor = await conn.execute(
                # [FIX] Use 'settings' object
                f"SELECT id, input_text, output_text FROM {settings.CORPUS_TABLE_NAME} WHERE id BETWEEN ? AND ?",
                (start_id, end_id),
            )
            records = await cursor.fetchall()

        if not records:
            # [FIX] Added 'await'
            await safe_notification("Export Failed", f"No records found in range {start_id}-{end_id}.")
            return

        context_data = [{"id": r[0], "user_input": r[1], "ai_output": r[2]} for r in records]
        export_path = Path(f"./context/session_range_{start_id}_to_{end_id}.json")
        
        def _write_file():
            export_path.parent.mkdir(exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(context_data, f, ensure_ascii=False, indent=4)
        
        await asyncio.to_thread(_write_file)
        
        # [FIX] Added 'await'
        await safe_notification("Export Complete", f"Saved {len(records)} items to {export_path}")
        print(f"✅ {Colors.GREEN}[Export Complete] Saved {len(records)} interactions.{Colors.ENDC}")


# In core/hotkey_handlers.py
# REPLACE the existing search_codebase and search_codebase_task functions with this block.

async def search_codebase(search_term: str):
    """[ASYNC DISPATCHER] Handles Alt+K: Dispatches the search task to the background."""
    if not fast_grep_engine:
        await safe_notification("Search Failed", "fast_grep_engine is not available.")
        return
    if state.app_controller_lock.locked():
        await safe_notification("System Busy", "Another heavy task is running.")
        return
    
    print(f"\n{Colors.BLUE}[Async Handler] Codebase search task started in background...{Colors.ENDC}")
    # [FIX] Added 'await'
    await safe_notification("Search Started", "Searching codebase in the background...")
    asyncio.create_task(search_codebase_task(search_term))

async def search_codebase_task(search_term: str):
    """[ASYNC WORKER] Performs the C++ engine search."""
    async with state.app_controller_lock:
        try:
            # [FIX] Use 'settings' object instead of 'config'
            search_path = str(settings.HOME_DIR)
            results = await asyncio.to_thread(fast_grep_engine.search_content, path=search_path, term=search_term)
            if not results:
                await safe_notification("Search Complete", f"No results found for '{search_term}'.")
                return

            summary = f"Found {len(results)} results."
            # [FIX] Added 'await'
            await safe_notification("Codebase Search Complete", summary)
            print(f"✅ {Colors.GREEN}[BG Search Complete] {summary}{Colors.ENDC}")
            for line in results[:10]:
                print(f"{Colors.CYAN}{line}{Colors.ENDC}")
        except Exception as e:
            print(f"❌ {Colors.RED}[Code Search Error] An unexpected error occurred: {e}{Colors.ENDC}")
            traceback.print_exc()
            await safe_notification("Code Search Error", "An error occurred in the background task.")
        finally:
            pass # Lock released automatically

# In core/hotkey_handlers.py
# REPLACE the existing analyze_personal_history and advisor_task functions with this block.

async def analyze_personal_history(current_topic: str):
    """[ASYNC DISPATCHER] Handles Alt+J: The 'Personal Memory Advisor' feature."""
    if not state.IS_QDRANT_DB_READY:
        await safe_notification("Error", "Vector Database is not ready.")
        return
    if state.app_controller_lock.locked():
        await safe_notification("System Busy", "Another heavy task is running.")
        return

    print(f"\n{Colors.MAGENTA}[Async Handler] Memory Advisor task started...{Colors.ENDC}")
    # [FIX] Added 'await' before safe_notification
    await safe_notification("Analysis Started", "The AI is thinking...")
    asyncio.create_task(advisor_task(current_topic))

async def advisor_task(current_topic: str):
    """[ASYNC WORKER] The background worker for the Memory Advisor."""
    async with state.app_controller_lock:
        try:
            # [FIX] Added 'await' before the async function call
            query_vector = await ai_services.generate_text_vector(current_topic)
            if not query_vector:
                await safe_notification("Vectorization Failed", "Could not generate vector.")
                return

            search_results = await asyncio.to_thread(
                state.QDRANT_CLIENT.query_points,
                # [FIX] Use 'settings' object instead of 'config'
                collection_name=settings.QDRANT_COLLECTION_NAME, query=query_vector, limit=3
            )
            
            if not search_results.points:
                await safe_notification("No Related History", "Could not find similar interactions.")
                return

            retrieved_history = "\n\n".join([f"--- [Past Interaction] ---\n{res.payload.get('full_turn', '')}" for res in search_results.points])
            master_prompt = f"""
# Your Role
You are my AI Strategic Advisor and Personal Knowledge Curator. Help me learn from my past actions.
# My Current Topic
"{current_topic}"
# Relevant Past Interactions
{retrieved_history}
# Your Task
Provide a concise, strategic analysis with these sections:
1.  **Past Achievements Summary:** What have I already accomplished?
2.  **Untapped Knowledge & Gaps:** What ideas did I never follow up on?
3.  **Strategic Next Steps:** Provide a clear, prioritized list of 2-3 actionable next steps.
"""
            final_analysis = await ai_services.run_ai_task(master_prompt)
            if not final_analysis:
                await safe_notification("Analysis Failed", "AI model did not return a response.")
                return

            await asyncio.to_thread(pyperclip.copy, final_analysis)
            # [FIX] Added 'await'
            await safe_notification("Personal Analysis Complete", "Results copied.")
            print(f"{Colors.YELLOW}--- [ Personal Memory Advisor | Complete ] ---{Colors.ENDC}")
            print(f"{Colors.GREEN}{final_analysis}{Colors.ENDC}")
        except Exception as e:
            # Add robust error logging for background tasks
            print(f"❌ {Colors.RED}[Advisor Task Error] An unexpected error occurred: {e}{Colors.ENDC}")
            traceback.print_exc()
            await safe_notification("Advisor Error", "An unexpected error occurred in the background task.")
        finally:
            pass # The 'async with' block handles the lock release

# In core/hotkey_handlers.py
# REPLACE the existing talent pool search functions.

async def find_and_search_talent_pools(job_description: str):
    """[ASYNC DISPATCHER] Handles Alt+M: Dispatches talent search to the background."""
    if not state.IS_QDRANT_DB_READY:
        await safe_notification("Error", "Vector Database is not ready.")
        return
    if state.app_controller_lock.locked():
        await safe_notification("System Busy", "Another search is in progress.")
        return
    
    print(f"\n{Colors.BLUE}[Async Handler] Talent pool search task started...{Colors.ENDC}")
    await safe_notification("Search Started", "Scanning all talent pools in the background.")
    asyncio.create_task(find_and_search_talent_pools_task(job_description))

async def find_and_search_talent_pools_task(job_description: str):
    """[ASYNC WORKER] Performs the parallel brute-force search across all collections."""
    async with state.app_controller_lock:
        try:
            collections_res = await asyncio.to_thread(state.QDRANT_CLIENT.get_collections)
            collections = [c.name for c in collections_res.collections]
            query_vector = await ai_services.generate_text_vector(job_description)
            
            async def search_one_collection(name):
                try:
                    return await asyncio.to_thread(
                        state.QDRANT_CLIENT.query_points,
                        collection_name=name, query=query_vector, limit=5, with_payload=True
                    )
                except Exception: return None

            tasks = [search_one_collection(name) for name in collections]
            all_search_results = await asyncio.gather(*tasks)

            all_results = []
            for res in all_search_results:
                if res: all_results.extend(res.points)

            if not all_results:
                await safe_notification("Search Complete", "No matching candidates found.")
                return
                
            all_results.sort(key=lambda r: r.score, reverse=True)
            top_results_text = "--- [ Top 5 Overall Candidates Across All Talent Pools ] ---\n\n"
            for i, result in enumerate(all_results[:5]):
                payload = result.payload or {}
                snippet = (payload.get("full_turn") or payload.get("text", "N/A")).split("\n")[0]
                top_results_text += f"#{i+1}: Match Score: {result.score*100:.2f}%\n   - Snippet: {snippet}...\n\n"
            
            await asyncio.to_thread(pyperclip.copy, top_results_text)
            await safe_notification("Talent Search Complete", f"Found {len(all_results)} total candidates. Top 5 copied.")
            print(f"{Colors.YELLOW}{top_results_text}{Colors.ENDC}")
        except Exception as e:
            print(f"❌ {Colors.RED}[Talent Search Error] An unexpected error occurred: {e}{Colors.ENDC}")
            traceback.print_exc()
            await safe_notification("Talent Search Error", "An error occurred in the background.")
