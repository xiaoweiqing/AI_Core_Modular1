# config.py (最终融合版)

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ==============================================================================
#      【【【 1. 模型切换的“总开关”和配置中心，放在最前面 】】】
# ==============================================================================
MODEL_CONFIGS = {
    "minilm": {
        "path": "./all-MiniLM-L6-v2",
        "dimension": 384,
        "qdrant_collection_name": "dialogue_pairs_v2",
        "qdrant_risk_analysis_collection": "risk_analysis_history_v1",
        "qdrant_constitution_collection": "personal_constitution_384d_v1", # <-- ADD THIS LINE
    },
    "gemma": {
        "path": "./embeddinggemma-300m",
        "dimension": 768,
        "qdrant_collection_name": "gemma_dialogue_pairs_768d_v1",
        "qdrant_risk_analysis_collection": "gemma_risk_analysis_768d_v1",
        "qdrant_constitution_collection": "gemma_constitution_768d_v1", # <-- AND ADD THIS LINE
    }
}

# ---  ⚠️  这是你的“总开关”  ⚠️ ---
# ---  想用哪个模型，就把这里的名字改成哪个，"gemma" 或者 "minilm" ---
CURRENT_MODEL_NAME = "gemma"
ACTIVE_MODEL_CONFIG = MODEL_CONFIGS[CURRENT_MODEL_NAME]


# ==============================================================================
#      【【【 2. 全新的、融合了所有功能的 AppSettings 类 】】】
# ==============================================================================
class AppSettings(BaseSettings):
    """
    Defines and validates ALL application settings.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False)

    # --- 首先，声明你 .env 文件中所有的自定义变量，让它们变得合法 ---
    google_ai_key: Optional[str] = None
    notion_token: Optional[str] = None
    google_search_api_key: Optional[str] = None
    google_search_cx: Optional[str] = None
    core_brain_database_id: Optional[str] = None
    toolbox_log_database_id: Optional[str] = None
    daily_review_database_id: Optional[str] = None
    training_hub_database_id: Optional[str] = None
    inbox_database_id: Optional[str] = None
    jd_hub_database_id: Optional[str] = None
    candidate_db_id: Optional[str] = None
    candidate_profile_hub_db_id: Optional[str] = None

    # --- 其次，定义程序需要的其他固定配置 ---
    HOME_DIR: Path = Path.home()
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    KEEP_AUDIO_FILES: bool = True
    RECORD_CHUNK_SECONDS: int = Field(60, gt=0, le=3600)
    CORPUS_TABLE_NAME: str = "training_data"
    DAILY_RECORDS_TABLE_NAME: str = "records"
    RISK_ASSESSMENT_TABLE_NAME: str = "assessments"
    VOICE_TRANSCRIPTS_TABLE_NAME: str = "transcripts"
    CONCISE_QA_TABLE_NAME: str = "qa_records"
# --- ADD THESE TWO NEW LINES BELOW ---
    CONSTITUTION_TABLE_NAME: str = "principles"

    @property
    def CONSTITUTION_DB(self) -> Path: return self.HOME_DIR / "personal_constitution.sqlite"
    # --- END OF ADDITION ---    
    # --- 最后，使用 @property 让向量数据库的配置“动”起来 ---
    @property
    def QDRANT_COLLECTION_NAME(self) -> str:
        """每次需要时，都重新从总开关获取正确的集合名"""
        return ACTIVE_MODEL_CONFIG["qdrant_collection_name"]

    @property
    def QDRANT_RISK_ANALYSIS_COLLECTION(self) -> str:
        """每次需要时，都重新从总开关获取正确的风险分析集合名"""
        return ACTIVE_MODEL_CONFIG["qdrant_risk_analysis_collection"]

    @property
    def VECTOR_DIMENSION(self) -> int:
        """每次需要时，都重新从总开关获取正确的向量维度"""
        return ACTIVE_MODEL_CONFIG["dimension"]
# In config.py, inside the AppSettings class

    @property
    def QDRANT_CONSTITUTION_COLLECTION(self) -> str:
        """Dynamically gets the correct constitution collection name from the active model config."""
        return ACTIVE_MODEL_CONFIG["qdrant_constitution_collection"]
    # --- 各种动态路径的 @property (保持不变) ---
# --- ADD THIS NEW LINE ---
    # This defines the minimum similarity score for an item to be considered a duplicate.
    # 0.995 is a good starting point (meaning 99.5% similar).
    SIMILARITY_THRESHOLD: float = 0.995

    @property
    def IPC_DIR(self) -> Path: return self.HOME_DIR / ".ai_ecosystem_ipc"
    @property
    def AUDIO_ARCHIVE_DIR(self) -> Path: return self.HOME_DIR / "audio_archives"
    @property
    def CORPUS_DB(self) -> Path: return self.HOME_DIR / "ai_training_corpus.sqlite"
    @property
    def DAILY_RECORDS_DB(self) -> Path: return self.HOME_DIR / "gemini_daily_records.sqlite"
    @property
    def RISK_ASSESSMENT_DB(self) -> Path: return self.HOME_DIR / "personal_risk_assessments.sqlite"
    @property
    def VOICE_TRANSCRIPTS_DB(self) -> Path: return self.HOME_DIR / "voice_transcripts.sqlite"
    @property
    def CONCISE_QA_DB(self) -> Path: return self.HOME_DIR / "concise_qa_archive.sqlite"


# ==============================================================================
#      【【【 3. 创建全局可用的 settings 实例和 TRIGGER_FILES (保持不变) 】】】
# ==============================================================================
try:
    settings = AppSettings()
except Exception as e:
    print(f"FATAL: Configuration error - {e}")
    exit(1)

TRIGGER_FILES = {
    "translate_to_en": settings.IPC_DIR / "trigger_translate_to_en",
    "translate_to_zh": settings.IPC_DIR / "trigger_translate_to_zh",
    "optimize_prompt": settings.IPC_DIR / "trigger_optimize_prompt",
    "read_aloud": settings.IPC_DIR / "trigger_read_aloud",
    "toggle_read_aloud": settings.IPC_DIR / "trigger_toggle_read_aloud_mode",
    "get_concise_answer": settings.IPC_DIR / "trigger_get_concise_answer",
    "personal_risk_analysis": settings.IPC_DIR / "trigger_personal_risk_analysis",
    "export_range_context": settings.IPC_DIR / "trigger_export_range_context",
    "save_input": settings.IPC_DIR / "trigger_save_input",
    "save_output": settings.IPC_DIR / "trigger_save_output",
    "cancel_turn": settings.IPC_DIR / "trigger_cancel_turn",
    "mark_high_quality": settings.IPC_DIR / "trigger_mark_high_quality",
    "voice_to_text": settings.IPC_DIR / "trigger_voice_to_text",
    "meeting_mode": settings.IPC_DIR / "trigger_meeting_mode",
    "codebase_search": settings.IPC_DIR / "trigger_codebase_search",
    "personal_memory_advisor": settings.IPC_DIR / "trigger_memory_advisor",
    "talent_pool_search": settings.IPC_DIR / "trigger_talent_pool_search",
# --- ADD THIS NEW LINE AT THE END OF THE DICTIONARY ---
    "import_constitution_principle": settings.IPC_DIR / "trigger_import_constitution_principle",
}
