"""Make sure data exists: demo DB + policy PDF if missing, then (re)build the search index if needed.
Safe to run on every boot. Drop your real blinkit.db / policy PDF into backend/data and it uses those."""
from app.config import settings


def bootstrap() -> dict:
    from app.llm import llm
    from app.rag import build_index
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    made = []
    if not settings.db_path.exists():
        from scripts.make_demo_data import make_db
        make_db(settings.db_path)
        made.append("demo database")
    if not settings.pdf_path.exists():
        from scripts.make_demo_data import make_policy_pdf
        make_policy_pdf(settings.pdf_path)
        made.append("demo policy pdf")
    chunks = settings.index_dir / "chunks.json"
    vecs = settings.index_dir / "vectors.npy"
    stale = (not chunks.exists()) or chunks.stat().st_mtime < settings.pdf_path.stat().st_mtime
    need_vectors = llm.available and not vecs.exists()
    info = {"created": made}
    if stale or need_vectors:
        info["index"] = build_index(settings.pdf_path, settings.index_dir, llm.embed_docs if llm.available else None)
    return info


if __name__ == "__main__":
    print(bootstrap())
