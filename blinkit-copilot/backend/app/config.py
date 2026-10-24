"""Central settings. Everything comes from environment variables (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    data_dir = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    db_path = Path(os.getenv("BLINKIT_DB", "")) if os.getenv("BLINKIT_DB") else data_dir / "blinkit.db"
    pdf_path = Path(os.getenv("POLICY_PDF", "")) if os.getenv("POLICY_PDF") else data_dir / "policy.pdf"
    ops_db_path = data_dir / "ops.db"          # traces, approvals, feedback (read-write)
    index_dir = data_dir / "index"             # chunks.json + vectors.npy

    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    embed_model = os.getenv("EMBED_MODEL", "gemini-embedding-001")

    app_api_key = os.getenv("APP_API_KEY", "")  # optional shared secret for the demo deployment
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))

    max_question_chars = 1500
    sql_row_limit = 50
    sql_timeout_s = 5.0
    agent_max_steps = int(os.getenv("AGENT_MAX_STEPS", "8"))
    auto_bootstrap = _bool("AUTO_BOOTSTRAP", True)  # create demo data + index on first boot if missing


settings = Settings()
