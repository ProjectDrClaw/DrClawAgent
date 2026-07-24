# -*- coding: utf-8 -*-
from pathlib import Path
from dotenv import load_dotenv

from .env_resolve import get_env as _resolve_env

# Load .env file from project root before reading any env vars
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


def _get_env(key: str, default: str = "") -> str:
    """Look up env var: DRCLAW_* > QWENPAW_* > COPAW_*."""
    return _resolve_env(key, default)


class EnvVarLoader:
    """Utility to load and parse environment variables with type safety
    and defaults.  Pass DRCLAW_* keys; QWENPAW_* / COPAW_* fallbacks are
    resolved automatically inside _get_env.
    """

    @staticmethod
    def get_bool(env_var: str, default: bool = False) -> bool:
        """Get a boolean environment variable,
        interpreting common truthy values."""
        val = _get_env(env_var, str(default)).lower()
        return val in ("true", "1", "yes")

    @staticmethod
    def get_float(
        env_var: str,
        default: float = 0.0,
        min_value: float | None = None,
        max_value: float | None = None,
        allow_inf: bool = False,
    ) -> float:
        """Get a float environment variable with optional bounds
        and infinity handling."""
        try:
            value = float(_get_env(env_var, str(default)))
            if min_value is not None and value < min_value:
                return min_value
            if max_value is not None and value > max_value:
                return max_value
            if not allow_inf and (
                value == float("inf") or value == float("-inf")
            ):
                return default
            return value
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_int(
        env_var: str,
        default: int = 0,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """Get an integer environment variable with optional bounds."""
        try:
            value = int(_get_env(env_var, str(default)))
            if min_value is not None and value < min_value:
                return min_value
            if max_value is not None and value > max_value:
                return max_value
            return value
        except (TypeError, ValueError):
            return default

    @staticmethod
    def get_str(env_var: str, default: str = "") -> str:
        """Get a string environment variable with a default fallback."""
        return _get_env(env_var, default)


CUSTOM_AGENT_STARTUP_CONCURRENCY_ENV = (
    "DRCLAW_CUSTOM_AGENT_STARTUP_CONCURRENCY"
)
DEFAULT_CUSTOM_AGENT_STARTUP_CONCURRENCY = 5
CUSTOM_AGENT_STARTUP_CONCURRENCY = EnvVarLoader.get_int(
    CUSTOM_AGENT_STARTUP_CONCURRENCY_ENV,
    default=DEFAULT_CUSTOM_AGENT_STARTUP_CONCURRENCY,
    min_value=1,
)


# WORKING_DIR priority:
# 1. DRCLAW_WORKING_DIR (or QWENPAW_/COPAW_ legacy) env var is set 鈫?use it
# 2. ~/.copaw exists (legacy installation) 鈫?use it as-is
# 3. ~/.qwenpaw exists (legacy installation) 鈫?use it as-is
# 4. Default 鈫?~/.drclaw
_explicit_working_dir = _get_env("DRCLAW_WORKING_DIR")
if _explicit_working_dir:
    WORKING_DIR = Path(_explicit_working_dir).expanduser().resolve()
else:
    _legacy_copaw_dir = Path("~/.copaw").expanduser()
    _legacy_qwenpaw_dir = Path("~/.qwenpaw").expanduser()
    if _legacy_copaw_dir.exists():
        WORKING_DIR = _legacy_copaw_dir.resolve()
    elif _legacy_qwenpaw_dir.exists():
        WORKING_DIR = _legacy_qwenpaw_dir.resolve()
    else:
        WORKING_DIR = Path("~/.drclaw").expanduser().resolve()
SECRET_DIR = (
    Path(
        EnvVarLoader.get_str(
            "DRCLAW_SECRET_DIR",
            f"{WORKING_DIR}.secret",
        ),
    )
    .expanduser()
    .resolve()
)

# Env key for overriding the OS keychain account used for the master key.
KEYRING_ACCOUNT_ENV = "DRCLAW_KEYRING_ACCOUNT"

PROJECT_NAME = "DrClaw"

# Message metadata tags shared across agent middleware and memory managers.
QWENPAW_MESSAGE_TAG_KEY = "DRCLAW_tag"
AUTO_MEMORY_SEARCH_BLOCK_IDS_KEY = "auto_memory_search_block_ids"
EXTERNAL_USER_QUERY_MESSAGE_TAG = "external_user_query"
AUTO_CONTINUE_MESSAGE_TAG = "auto_continue"
LOOP_CONTINUATION_MESSAGE_TAG = "loop_continuation"
RUBRIC_EVALUATION_MESSAGE_TAG = "rubric_evaluation"
# User-role messages the runtime injects to keep a turn going. They are NOT
# new requests: the scroll active-turn anchor (live scan + SQL floor) must
# skip them, or the anchor jumps to the stub and the REAL request becomes
# evictable/searchable again (the #5746 failure mode, loop-session flavor).
SYNTHETIC_USER_MESSAGE_TAGS = frozenset(
    {
        AUTO_CONTINUE_MESSAGE_TAG,
        LOOP_CONTINUATION_MESSAGE_TAG,
        RUBRIC_EVALUATION_MESSAGE_TAG,
    },
)
AUTO_MEMORY_SEARCH_TEXT = (
    "I'll check memory for relevant context before answering."
)
AUTO_MEMORY_SEARCH_THINKING_PREFIX = (
    "I should search long-term memory before answering."
)

# Subdirectory name inside each agent's workspace that holds cloned / imported
# coding projects.
# Full path = <workspace_dir> / CODING_PROJECT_SUBDIR / <name>
CODING_PROJECT_SUBDIR = "coding_projects"


def _resolve_docs_dir() -> Path | None:
    """查找 Dr.Claw 文档目录（兼容包内嵌与源码树）。"""
    _pkg_docs = Path(__file__).resolve().parent / "docs"
    if _pkg_docs.is_dir() and any(_pkg_docs.glob("*.md")):
        return _pkg_docs
    _repo_docs = Path(__file__).resolve().parents[2] / "docs"
    if _repo_docs.is_dir() and any(_repo_docs.glob("*.md")):
        return _repo_docs
    return None


DOCS_DIR: Path | None = _resolve_docs_dir()

# Default media directory for channels (cross-platform)
DEFAULT_MEDIA_DIR = WORKING_DIR / "media"

# Default local provider directory
DEFAULT_LOCAL_PROVIDER_DIR = WORKING_DIR / "local_models"

JOBS_FILE = EnvVarLoader.get_str("DRCLAW_JOBS_FILE", "jobs.json")

CHATS_FILE = EnvVarLoader.get_str("DRCLAW_CHATS_FILE", "chats.json")


# Builtin Q&A helper profile. agent_id is stable for existing workspaces
# and agent.json; do not rename lightly.
def _discover_agent_languages() -> frozenset[str]:
    md_root = Path(__file__).resolve().parent / "agents" / "md_files"
    if md_root.is_dir():
        langs = {
            d.name
            for d in md_root.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and any(d.glob("*.md"))
        }
        if langs:
            return frozenset(langs)
    return frozenset({"en", "zh", "ru"})


SUPPORTED_AGENT_LANGUAGES: frozenset[str] = _discover_agent_languages()

TOKEN_USAGE_FILE = EnvVarLoader.get_str(
    "DRCLAW_TOKEN_USAGE_FILE",
    "token_usage.json",
)

CONFIG_FILE = EnvVarLoader.get_str("DRCLAW_CONFIG_FILE", "config.json")

HEARTBEAT_FILE = EnvVarLoader.get_str("DRCLAW_HEARTBEAT_FILE", "HEARTBEAT.md")
HEARTBEAT_DEFAULT_EVERY = "6h"
HEARTBEAT_DEFAULT_TARGET = "main"
HEARTBEAT_DEFAULT_TIMEOUT_SECONDS = 300
HEARTBEAT_MAX_TIMEOUT_SECONDS = 3600
HEARTBEAT_TARGET_LAST = "last"
HEARTBEAT_TARGET_INBOX = "inbox"

# Debug history file for /dump_history and /load_history commands
DEBUG_HISTORY_FILE = EnvVarLoader.get_str(
    "DRCLAW_DEBUG_HISTORY_FILE",
    "debug_history.jsonl",
)
MAX_LOAD_HISTORY_COUNT = 10000

# Env key for app log level (used by CLI and app load for reload child).
LOG_LEVEL_ENV = "DRCLAW_LOG_LEVEL"

# Fixed desktop backend port. When set, get_stable_port() uses this port
# instead of auto-assigning. When unset, desktop backends default to 8088.
DEFAULT_DESKTOP_PORT = 8088
# Default bind address for desktop backends
# (Tauri sidecar and ``drclaw desktop``).
DEFAULT_DESKTOP_API_HOST = "0.0.0.0"
DRCLAW_DESKTOP_PORT = _get_env("DRCLAW_DESKTOP_PORT")
# 兼容旧代码导入
QWENPAW_DESKTOP_PORT = DRCLAW_DESKTOP_PORT

# Env to indicate running inside a container (e.g. Docker). Set to 1/true/yes.
RUNNING_IN_CONTAINER = EnvVarLoader.get_bool(
    "DRCLAW_RUNNING_IN_CONTAINER",
    False,
)

# Timeout in seconds for checking if a provider is reachable.
MODEL_PROVIDER_CHECK_TIMEOUT = EnvVarLoader.get_float(
    "DRCLAW_MODEL_PROVIDER_CHECK_TIMEOUT",
    5.0,
    min_value=0,
    allow_inf=False,
)

# Playwright: use system Chromium when set (e.g. in Docker).
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH_ENV = "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"

# When True, expose /docs, /redoc, /openapi.json
# (dev only; keep False in prod).
DOCS_ENABLED = EnvVarLoader.get_bool("DRCLAW_OPENAPI_DOCS", False)

# Memory directory
MEMORY_DIR = WORKING_DIR / "memory"

# Backup directory
BACKUP_DIR = (
    Path(
        EnvVarLoader.get_str(
            "DRCLAW_BACKUP_DIR",
            f"{WORKING_DIR}.backups",
        ),
    )
    .expanduser()
    .resolve()
)


# Plugin directory (installed via `qwenpaw plugin install`)
PLUGINS_DIR = WORKING_DIR / "plugins"

# Local models directory
MODELS_DIR = WORKING_DIR / "models"

MEMORY_COMPACT_KEEP_RECENT = EnvVarLoader.get_int(
    "DRCLAW_MEMORY_COMPACT_KEEP_RECENT",
    3,
    min_value=0,
)

# Memory compaction configuration
MEMORY_COMPACT_RATIO = EnvVarLoader.get_float(
    "DRCLAW_MEMORY_COMPACT_RATIO",
    0.7,
    min_value=0,
    allow_inf=False,
)

# CORS configuration 鈥?comma-separated list of allowed origins for dev mode.
# Example: QWENPAW_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
# When unset, CORS middleware is not applied.
CORS_ORIGINS = EnvVarLoader.get_str("DRCLAW_CORS_ORIGINS", "*").strip()

# Upload size limit (MB).  None = no limit.
UPLOAD_MAX_SIZE_MB: int | None = (
    int(v)
    if (v := EnvVarLoader.get_str("DRCLAW_UPLOAD_MAX_SIZE_MB", ""))
    .strip()
    .isdigit()
    else None
)

# LLM API retry configuration
LLM_MAX_RETRIES = EnvVarLoader.get_int(
    "DRCLAW_LLM_MAX_RETRIES",
    3,
    min_value=0,
)

LLM_BACKOFF_BASE = EnvVarLoader.get_float(
    "DRCLAW_LLM_BACKOFF_BASE",
    1.0,
    min_value=0.1,
)

LLM_BACKOFF_CAP = EnvVarLoader.get_float(
    "DRCLAW_LLM_BACKOFF_CAP",
    10.0,
    min_value=0.5,
)

# LLM concurrency control
# Maximum number of concurrent in-flight LLM calls; excess requests wait on
# the semaphore.  Tune to your API quota: start conservatively at 3-5 and
# increase (e.g. OpenAI Tier 1 ~500 QPM allows ~25 at 3 s/call average).
LLM_MAX_CONCURRENT = EnvVarLoader.get_int(
    "DRCLAW_LLM_MAX_CONCURRENT",
    10,
    min_value=1,
)

# Maximum queries per minute (QPM), enforced via a 60-second sliding window.
# New requests that would exceed this limit will wait before being dispatched
# to the API 鈥?proactively preventing 429s rather than reacting to them.
# 0 = unlimited (disabled).
# Examples: Anthropic Tier-1 鈮?50 QPM; OpenAI Tier-1 鈮?500 QPM.
LLM_MAX_QPM = EnvVarLoader.get_int(
    "DRCLAW_LLM_MAX_QPM",
    600,
    min_value=0,
)

# Default global pause duration (seconds) applied to all waiters when a 429
# is received.  Overridden by the API's Retry-After header when present.
LLM_RATE_LIMIT_PAUSE = EnvVarLoader.get_float(
    "DRCLAW_LLM_RATE_LIMIT_PAUSE",
    5.0,
    min_value=1.0,
)

# Random jitter range (seconds) added on top of the pause remaining time so
# concurrent waiters stagger their wake-up and avoid a new burst.
LLM_RATE_LIMIT_JITTER = EnvVarLoader.get_float(
    "DRCLAW_LLM_RATE_LIMIT_JITTER",
    1.0,
    min_value=0.0,
)

# Maximum time (seconds) a caller will wait for a semaphore slot before
# giving up with a RuntimeError rather than blocking indefinitely.
LLM_ACQUIRE_TIMEOUT = EnvVarLoader.get_float(
    "DRCLAW_LLM_ACQUIRE_TIMEOUT",
    300.0,
    min_value=10.0,
)

# Tool guard approval timeout (seconds).
try:
    TOOL_GUARD_APPROVAL_TIMEOUT_SECONDS = max(
        float(
            _get_env("DRCLAW_TOOL_GUARD_APPROVAL_TIMEOUT_SECONDS", "300"),
        ),
        1.0,
    )
except (TypeError, ValueError):
    TOOL_GUARD_APPROVAL_TIMEOUT_SECONDS = 300.0


# Tool guard approval heartbeat interval (seconds).
# Sends periodic heartbeat messages during approval wait to keep SSE
# connection alive. Should be less than browser/proxy timeout (30-60s).
try:
    TOOL_GUARD_APPROVAL_HEARTBEAT_INTERVAL = max(
        float(
            _get_env("DRCLAW_TOOL_GUARD_APPROVAL_HEARTBEAT_INTERVAL", "15"),
        ),
        5.0,
    )
except (TypeError, ValueError):
    TOOL_GUARD_APPROVAL_HEARTBEAT_INTERVAL = 15.0

# Marker prepended to every truncation notice.
# Format:
#   <<<TRUNCATED>>>
#   The output above was truncated.
#   The full content is saved to the file and contains Z lines in total.
#   This excerpt starts at line X and covers the next N bytes.
#   If the current content is not enough, call `read_file` with
#   file_path=<path> start_line=Y to read more.
#
# Split output on this marker to recover the original (untruncated) portion:
#   original = output.split(TRUNCATION_NOTICE_MARKER)[0]
TRUNCATION_NOTICE_MARKER = "<<<TRUNCATED>>>"

# Placeholder text used when media blocks are stripped from messages
# because the model does not support multimodal content.
MEDIA_UNSUPPORTED_PLACEHOLDER = (
    "[Media content removed - model does not support this media type]"
)
