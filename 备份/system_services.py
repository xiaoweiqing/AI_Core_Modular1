# core/system_services.py

import json
import sqlite3
from datetime import datetime, timezone, timedelta

# Import our custom modules
import config
from core import state
from core.hotkey_handlers import process_metadata_and_vectorize # We re-use this background task
from utils.helpers import Colors

def run_startup_maintenance():
    """A master function to run all startup checks and cleanup routines."""
    print("\n--- Running System Maintenance ---")
    cleanup_old_orphans()
    cleanup_duplicates()
    process_pending_tasks_on_startup()
    print("--------------------------------\n")

def cleanup_duplicates():
    """Performs startup deduplication check on the main corpus database."""
    print(">> [System] Checking for duplicate records...")
    try:
        with state.db_lock:
            conn = sqlite3.connect(config.CORPUS_DB, check_same_thread=False)
            cursor = conn.cursor()
            query = f"""
                DELETE FROM {config.CORPUS_TABLE_NAME}
                WHERE id IN (
                    SELECT id FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (PARTITION BY input_text ORDER BY id) as rn
                        FROM {config.CORPUS_TABLE_NAME}
                    ) t WHERE t.rn > 1
                )"""
            cursor.execute(query)
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
        if deleted_count > 0:
            print(f"   ✅ [Cleanup] Found and deleted {deleted_count} duplicate record(s).")
        else:
            print("   -> No duplicates found. Database is clean.")
    except Exception as e:
        print(f"   ❌ {Colors.RED}[Deduplication Error] An error occurred: {e}{Colors.ENDC}")


def cleanup_old_orphans():
    """Cleans up any records that were started (Alt+S) but not finished (Alt+D) within 24 hours."""
    print(">> [System] Checking for old, incomplete records...")
    try:
        with state.db_lock:
            conn = sqlite3.connect(config.CORPUS_DB, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {config.CORPUS_TABLE_NAME} WHERE status = 'pending_output' AND id < (SELECT MAX(id) - 10 FROM {config.CORPUS_TABLE_NAME})")
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
        if deleted_count > 0:
            print(f"   ✅ [Cleanup] Deleted {deleted_count} old orphaned record(s).")
        else:
            print("   -> No old orphaned records found.")
    except Exception as e:
        print(f"   ❌ {Colors.RED}[Cleanup Error] An error occurred: {e}{Colors.ENDC}")


def process_pending_tasks_on_startup():
    """Finds any records that were finished but not vectorized and queues them for processing."""
    print(">> [System] Checking for pending background tasks from the last session...")
    try:
        with state.db_lock:
            conn = sqlite3.connect(config.CORPUS_DB, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(f"SELECT id FROM {config.CORPUS_TABLE_NAME} WHERE status = 'pending_summaries'")
            pending_records = cursor.fetchall()
            conn.close()

        if pending_records:
            print(f"   -> {Colors.YELLOW}Found {len(pending_records)} pending task(s). Queueing them...{Colors.ENDC}")
            for record in pending_records:
                record_id = record[0]
                print(f"      - Queueing task for Record ID: {record_id}")
                state.background_task_executor.submit(process_metadata_and_vectorize, record_id, "output")
        else:
            print("   -> No pending tasks found. All records are fully processed.")
    except Exception as e:
        print(f"   ❌ {Colors.RED}[Pending Task Error] Failed to queue pending tasks: {e}{Colors.ENDC}")
