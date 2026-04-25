import os
from typing import Iterable, List, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
CHECKPOINT_DIR = os.path.join(BASE_DIR, "checkpoints")
DB_DIR = os.path.join(BASE_DIR, "db")
DB_PATH = os.path.join(DB_DIR, "chroma_store")
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")


def load_env_files(paths: Optional[Iterable[str]] = None) -> str:
    env_paths = list(paths or (
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(BASE_DIR, ".env"),
    ))
    for path in env_paths:
        if path and os.path.exists(path):
            if load_dotenv is not None:
                load_dotenv(path, override=False)
            else:
                with open(path, "r", encoding="utf-8") as env_file:
                    for raw_line in env_file:
                        line = raw_line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())
            return path
    return ""


LOADED_ENV_FILE = load_env_files()


def _get_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _get_env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _get_env_list(name: str, default: List[str]) -> List[str]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    values = [item.strip() for item in raw_value.split(",")]
    return [item for item in values if item] or default


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


TRACKNET_PATH = os.path.join(CHECKPOINT_DIR, "TrackNet_best.pt")
INPAINTNET_PATH = os.path.join(CHECKPOINT_DIR, "InpaintNet_best.pt")
YOLO_PATH = os.path.join(CHECKPOINT_DIR, "yolov8n-pose.pt")

WIDTH = 512
HEIGHT = 288
COOR_TH = 0.5

COURT_LENGTH = 13.40
COURT_WIDTH_DOUBLES = 6.10
COURT_WIDTH_SINGLES = 5.18
SIDE_ALLEY_WIDTH = 0.46

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_UPLOAD_SIZE_MB = _get_env_int("EVOSMASH_MAX_UPLOAD_MB", 250)
CORS_ALLOW_ORIGINS = _get_env_list("EVOSMASH_CORS_ALLOW_ORIGINS", ["*"])
API_HOST = os.getenv("EVOSMASH_API_HOST", "0.0.0.0").strip() or "0.0.0.0"
API_PORT = _get_env_int("EVOSMASH_API_PORT", 8000)
LOG_LEVEL = os.getenv("EVOSMASH_LOG_LEVEL", "INFO").strip().upper() or "INFO"

LLM_API_KEY = os.getenv("EVOSMASH_LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("EVOSMASH_LLM_BASE_URL", "https://api.siliconflow.cn/v1").strip() or "https://api.siliconflow.cn/v1"
LLM_MODEL_NAME = os.getenv("EVOSMASH_LLM_MODEL_NAME", "deepseek-ai/DeepSeek-V3").strip() or "deepseek-ai/DeepSeek-V3"
LLM_TIMEOUT_SECONDS = _get_env_float("EVOSMASH_LLM_TIMEOUT_SECONDS", 20.0)
LLM_ENABLED = bool(LLM_API_KEY)


def ensure_runtime_directories() -> None:
    for path in (CHECKPOINT_DIR, DB_DIR, TEMP_DIR):
        os.makedirs(path, exist_ok=True)


def describe_runtime_config() -> dict:
    return {
        "api_host": API_HOST,
        "api_port": API_PORT,
        "cors_allow_origins": CORS_ALLOW_ORIGINS,
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,
        "log_level": LOG_LEVEL,
        "loaded_env_file": LOADED_ENV_FILE,
        "llm": {
            "enabled": LLM_ENABLED,
            "base_url": LLM_BASE_URL,
            "model_name": LLM_MODEL_NAME,
            "timeout_seconds": LLM_TIMEOUT_SECONDS,
            "api_key_preview": _mask_secret(LLM_API_KEY),
        },
    }


ensure_runtime_directories()
