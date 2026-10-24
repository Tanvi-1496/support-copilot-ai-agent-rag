import os, sys, tempfile
from pathlib import Path

# isolate tests: temp data dir, no API keys, no auto bootstrap on import
tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = tmp
os.environ["GOOGLE_API_KEY"] = ""
os.environ["APP_API_KEY"] = ""
os.environ["AUTO_BOOTSTRAP"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


@pytest.fixture(scope="session", autouse=True)
def demo_data():
    from app.config import settings
    from scripts.make_demo_data import make_db, make_policy_pdf
    from app.rag import build_index
    make_db(settings.db_path, n_orders=1500)
    make_policy_pdf(settings.pdf_path)
    build_index(settings.pdf_path, settings.index_dir, None)
    from app import tools
    from app.rag import load_index
    tools.set_index(load_index())
