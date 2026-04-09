# ==============================================================================
#      【【【 THIS IS THE COMPLETE, MODIFIED FILE 】】】
# ==============================================================================
# core/database_manager.py

import asyncio
import aiosqlite
import traceback
from pathlib import Path
from qdrant_client import QdrantClient, models

# Import our custom modules
from core import state
from config import settings # Import the settings object
from utils.helpers import Colors

async def setup_all_databases():
    """
    [ASYNC MASTER] Initializes all databases concurrently for maximum startup speed.
    """
    print("\n" + "="*70)
    print("--- Initializing All Databases Concurrently ---")

    tasks = [
        _initialize_sqlite_db("Corpus DB", settings.CORPUS_DB, f"CREATE TABLE IF NOT EXISTS {settings.CORPUS_TABLE_NAME} (id INTEGER PRIMARY KEY AUTOINCREMENT, input_text TEXT, output_text TEXT, metadata TEXT, status TEXT NOT NULL, quality_label TEXT)"),
        _initialize_sqlite_db("Daily Records DB", settings.DAILY_RECORDS_DB, f"CREATE TABLE IF NOT EXISTS {settings.DAILY_RECORDS_TABLE_NAME} (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, event_type TEXT NOT NULL, original_text TEXT, processed_text TEXT, meta_prompt TEXT, ai_summary TEXT, tags TEXT)"),
        _initialize_sqlite_db("Risk Assessment DB", settings.RISK_ASSESSMENT_DB, f"CREATE TABLE IF NOT EXISTS {settings.RISK_ASSESSMENT_TABLE_NAME} (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, input_situation TEXT NOT NULL, ai_full_response TEXT NOT NULL)"),
        _setup_voice_transcripts_db_with_migration(), # <-- THIS IS THE MODIFIED LINE
        _initialize_sqlite_db("Concise Q&A DB", settings.CONCISE_QA_DB, f"CREATE TABLE IF NOT EXISTS {settings.CONCISE_QA_TABLE_NAME} (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, user_query TEXT NOT NULL, ai_response TEXT NOT NULL)"),
        setup_vector_database()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    print("="*70 + "\n")

    all_successful = True
    for result in results:
        if isinstance(result, Exception) or result is False:
            all_successful = False
    
    if not all_successful:
        print(f"❌ {Colors.RED}[DB Manager] One or more database initializations failed.{Colors.ENDC}")

    return all_successful

async def _initialize_sqlite_db(db_name: str, db_path: Path, create_sql: str) -> bool:
    """
    [ASYNC HELPER] Initializes a single SQLite database table.
    """
    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(create_sql)
            await conn.commit()
        print(f"✅ {Colors.GREEN}[DB Manager] {db_name} is ready. (Path: {db_path}){Colors.ENDC}")
        return True
    except Exception as e:
        print(f"❌ {Colors.RED}[DB Error] {db_name} initialization failed: {e}{Colors.ENDC}")
        traceback.print_exc()
        return False

async def _setup_voice_transcripts_db_with_migration() -> bool:
    """
    [ASYNC HELPER] Initializes the Voice Transcripts DB and ensures the
    'session_id' column exists for meeting recordings.
    """
    db_name = "Voice Transcripts DB"
    db_path = settings.VOICE_TRANSCRIPTS_DB
    table_name = settings.VOICE_TRANSCRIPTS_TABLE_NAME
    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            # Step 1: Create the table if it doesn't exist (original logic)
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    language_detected TEXT NOT NULL,
                    transcribed_text TEXT NOT NULL
                )""")

            # Step 2: Try to add the new session_id column
            try:
                await conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN session_id TEXT"
                )
                print(f"   -> [DB Migration] Added 'session_id' column to transcripts table.")
            except aiosqlite.OperationalError as e:
                # This error is expected if the column already exists. We can ignore it.
                if "duplicate column name" not in str(e):
                    raise # Re-raise any other unexpected errors

            await conn.commit()
        print(f"✅ {Colors.GREEN}[DB Manager] {db_name} is ready. (Path: {db_path}){Colors.ENDC}")
        return True
    except Exception as e:
        print(f"❌ {Colors.RED}[DB Error] {db_name} initialization failed: {e}{Colors.ENDC}")
        traceback.print_exc()
        return False

async def setup_vector_database():
    """[ASYNC] Initializes the Qdrant client non-blockingly."""
    def _sync_setup_qdrant():
        try:
            print(">> [Vector DB] Preparing vector database client in background thread...")
            state.QDRANT_CLIENT = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

            collections = [c.name for c in state.QDRANT_CLIENT.get_collections().collections]
            
            # Check for the main collection
            if settings.QDRANT_COLLECTION_NAME not in collections:
                print(f"   -> [Vector DB] Collection '{settings.QDRANT_COLLECTION_NAME}' not found. Creating...")
                state.QDRANT_CLIENT.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=settings.VECTOR_DIMENSION,
                        distance=models.Distance.COSINE
                    ),
                )
            
            # ==============================================================================
            #      【【【 ADD THIS NEW BLOCK 】】】
            # ==============================================================================
            # Check for the new risk analysis collection
            if settings.QDRANT_RISK_ANALYSIS_COLLECTION not in collections:
                print(f"   -> [Vector DB] Collection '{settings.QDRANT_RISK_ANALYSIS_COLLECTION}' not found. Creating...")
                state.QDRANT_CLIENT.create_collection(
                    collection_name=settings.QDRANT_RISK_ANALYSIS_COLLECTION,
                    vectors_config=models.VectorParams(
                        size=settings.VECTOR_DIMENSION,
                        distance=models.Distance.COSINE
                    ),
                )
            # ==============================================================================
            #      【【【 END OF ADDITION 】】】
            # ==============================================================================

            state.IS_QDRANT_DB_READY = True
            print(f"✅ {Colors.GREEN}[Vector DB] Qdrant client is ready.{Colors.ENDC}")
            return True
        except Exception as e:
            print(f"❌ {Colors.RED}[Vector DB Error] Initialization failed. Is Qdrant running? Error: {e}")
            state.IS_QDRANT_DB_READY = False
            return False

    return await asyncio.to_thread(_sync_setup_qdrant)
# ==============================================================================
#      【【【 ADD THIS ENTIRE NEW BLOCK TO THE END OF THE FILE 】】】
# ==============================================================================

# Import the necessary modules at the top of core/database_manager.py
from core import ai_services
from utils.helpers import get_local_time_str, clean_text

async def log_daily_record(event_type: str, original_text: str, processed_text: str, meta_prompt: str = ""):
    """
    [ASYNC BG TASK] Logs an operation to the daily records database and
    generates an AI summary for it in the background.
    """
    print(f">> [Async Log] Recording '{event_type}' event to daily records DB...")
    try:
        # 1. Generate AI Summary Asynchronously
        summary_prompt = f"""
# Task
Analyze the user's action below and provide a concise, one-sentence summary in Chinese.
This summary should capture the core intent of the user's original text.

# Data
- **Action Type:** {event_type}
- **User's Original Text:** "{clean_text(original_text)}"
- **AI's Processed Text:** "{clean_text(processed_text)}"

# Your Output
Provide only the one-sentence Chinese summary.
"""
        # We now await the async version of the AI task
        ai_summary = await ai_services.run_ai_task(summary_prompt)
        if not ai_summary:
            ai_summary = "AI summary generation failed."  # Fallback

        # 2. Save to Database Asynchronously
        async with aiosqlite.connect(str(settings.DAILY_RECORDS_DB)) as conn:
            await conn.execute(
                f"""
                INSERT INTO {settings.DAILY_RECORDS_TABLE_NAME}
                (timestamp, event_type, original_text, processed_text, meta_prompt, ai_summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    get_local_time_str(),
                    event_type,
                    original_text,
                    processed_text,
                    meta_prompt,
                    ai_summary,
                ),
            )
            await conn.commit()
            
        print(f"✅ {Colors.GREEN}[Async Log Complete] Saved '{event_type}' event to daily logs.{Colors.ENDC}")

    except Exception as e:
        print(f"❌ {Colors.RED}[Async Log Error] Failed to log daily record: {e}{Colors.ENDC}")
        traceback.print_exc()
# ==============================================================================
#      【【【 END OF ADDITION 】】】
# ==============================================================================
