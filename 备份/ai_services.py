# ==============================================================================
#      【【【 1. REPLACE your entire import block with this one 】】】
# ==============================================================================
import os
import traceback
import asyncio  # The core async library
from langchain_openai import ChatOpenAI
from sentence_transformers import SentenceTransformer
from pathlib import Path

# We import our state module to access global variables
from core import state
from utils.helpers import Colors

# ==============================================================================
#      【【【 2. REPLACE all functions in the file with these async versions 】】】
# ==============================================================================

async def setup_api():
    """[ASYNC] Initializes the connection to the local LLM server in a non-blocking way."""
    local_api_url = "http://127.0.0.1:8087/v1"

    try:
        # Proxy cleaning is fast and synchronous, no changes needed here.
        for proxy_var in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
            if proxy_var in os.environ:
                print(f">> [Proxy Cleaner] Found and removed system proxy: {proxy_var}")
                del os.environ[proxy_var]

        print(f"{Colors.BLUE}>> [Async AI Service] Attempting to connect to local model: {local_api_url}{Colors.ENDC}")

        # The ChatOpenAI constructor is a blocking call. We run it in a separate thread.
        state.llm = await asyncio.to_thread(
            ChatOpenAI,
            openai_api_base=local_api_url,
            openai_api_key="na",
            model_name="local-model",
            temperature=0.3,
            request_timeout=300,
            streaming=False,
        )

        # The `invoke` call is also blocking (it waits for a network response).
        # We run this test connection in a thread as well.
        await asyncio.to_thread(state.llm.invoke, "Hi")

        print(f"✅ {Colors.GREEN}[Async AI Service] Connection successful! Local LLM is ready.{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"❌ {Colors.RED}[Async AI Error] Failed to connect to local model server.{Colors.ENDC}")
        print(f"   {Colors.YELLOW}Is your local AI service running? Error: {e}{Colors.ENDC}")
        return False


async def run_ai_task(prompt: str) -> str | None:
    """
    [ASYNC] Sends a prompt to the LLM non-blockingly and cleans the response.
    """
    try:
        if not state.llm:
            print(f"{Colors.RED}[Async AI Error] LLM not initialized. Cannot run task.{Colors.ENDC}")
            return None

        # The core change: `invoke` is blocking, so we run it in a thread
        # and await the result, freeing the main loop to do other work.
        response = await asyncio.to_thread(state.llm.invoke, prompt)
        
        raw_output = response.content
        cleaned_text = raw_output

        # The rest of the cleaning logic is fast string manipulation, so it
        # doesn't need to be run in a separate thread.
        if "</think>" in cleaned_text:
            _, cleaned_text = cleaned_text.split("</think>", 1)

        final_answer_marker = "<|channel|>final<|message|>"
        if final_answer_marker in cleaned_text:
            _, cleaned_text = cleaned_text.split(final_answer_marker, 1)

        return cleaned_text.strip()
    except Exception as e:
        print(f"❌ {Colors.RED}[Async AI Error] Task execution failed: {e}{Colors.ENDC}")
        traceback.print_exc()
        return None


async def setup_embedding_model():
    """[ASYNC] Loads the local sentence-transformer model without blocking the main thread."""
    try:
        model_path = "./all-MiniLM-L6-v2"
        if not Path(model_path).is_dir():
            print(f"❌ {Colors.RED}[Embedding Error] Model folder not found at '{model_path}'!{Colors.ENDC}")
            return False

        print(f">> [Async Embedding] Loading local model from: '{model_path}' in a background thread...")
        
        # SentenceTransformer() is a very heavy, blocking call (reads from disk,
        # allocates memory). We MUST run it in a thread.
        state.EMBEDDING_MODEL = await asyncio.to_thread(SentenceTransformer, model_path)
        
        print(f"✅ {Colors.GREEN}[Async Embedding] Model 'all-MiniLM-L6-v2' is ready.{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"❌ {Colors.RED}[Async Embedding Error] Failed to load local model: {e}{Colors.ENDC}")
        return False


async def generate_text_vector(text: str) -> list[float] | None:
    """[ASYNC] Generates a vector embedding for text without blocking the event loop."""
    try:
        if not state.EMBEDDING_MODEL:
            print(f"{Colors.RED}[Async Embedding Error] Embedding model not initialized.{Colors.ENDC}")
            return None
            
        # .encode() is a CPU-bound operation. For long texts, it can block.
        # Running it in a thread ensures the application remains responsive.
        vector = await asyncio.to_thread(state.EMBEDDING_MODEL.encode, text)
        
        return vector.tolist()
    except Exception as e:
        print(f"❌ {Colors.RED}[Async Embedding Error] Failed to encode text: {e}{Colors.ENDC}")
        return None
