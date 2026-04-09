# core/state.py

import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

# --- AI Model and Client Placeholders ---
# These will be initialized at startup.
llm = None
QDRANT_CLIENT = None
EMBEDDING_MODEL = None
WHISPER_MODEL = None

# --- Status Flags ---
IS_QDRANT_DB_READY = False
IS_RECORDING = False
MEETING_MODE_ACTIVE = False
READ_ALOUD_MODE_ENABLED = False

# --- Database Record Tracking ---
# Used for the Alt+S / Alt+D workflow.
last_record_id = None
last_completed_id = None

# --- Threading and Concurrency ---
# Locks to prevent race conditions when accessing shared resources.
app_controller_lock = threading.Lock() # Main lock for user-facing tasks.
db_lock = threading.Lock()             # For the main corpus.sqlite.
daily_db_lock = threading.Lock()       # For the daily_records.sqlite.
risk_db_lock = threading.Lock()        # For the risk_assessment.sqlite.
concise_qa_db_lock = threading.Lock()  # For the concise_qa.sqlite.

# --- Background Task Management ---
# A queue for audio files waiting to be transcribed.
transcription_queue = Queue()

# A thread pool with a single worker to run heavy background tasks sequentially.
# This ensures that vectorization and summarization don't slow down the main app.
print(">> [System] Initializing background task executor (max_workers=1)...")
background_task_executor = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix='BackgroundTask'
)

# --- Process and Thread Placeholders ---
# To hold references to running processes or threads.
tts_process = None
recorder_thread = None
