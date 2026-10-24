"""Policy RAG: PDF -> heading-aware chunks -> hybrid retrieval (BM25 + vectors, fused with RRF).

Why hybrid: policy questions mix exact terms ("Section 9", "60 seconds", "NO_PHOTO") that BM25 nails
with paraphrases ("how long till my money is back") that embeddings nail. RRF merges both rankings
without needing to tune score scales.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

from .config import settings

HEADING = re.compile(r"^(?:(?i:section)\s+\d{1,2}[\.:]?\s*\S.*|\d{1,2}(?:\.\d{1,2})*\.?\s+[A-Z][^\n]{3,80})$")
TOKEN = re.compile(r"[a-z0-9₹%]+")


@dataclass
class Chunk:
    id: int
    text: str
    page: int
    section: str


@dataclass
class Hit:
    chunk: Chunk
    score: float
    via: str  # "bm25", "vector" or "hybrid"


def tokenize(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    return [(i + 1, (p.extract_text() or "")) for i, p in enumerate(reader.pages)]


def chunk_pages(pages: list[tuple[int, str]], target: int = 900, overlap: int = 150) -> list[Chunk]:
    """Pack lines into ~target-char chunks. Headings start a new chunk and are remembered as the
    section label, so every chunk can be cited as 'p.4 - Refund timelines'."""
    chunks: list[Chunk] = []
    section, buf, buf_page = "Preamble", "", 1

    def flush():
        nonlocal buf
        text = buf.strip()
        if len(text) > 40:
            chunks.append(Chunk(len(chunks), f"{section}\n{text}" if not text.startswith(section) else text, buf_page, section))
        buf = buf[-overlap:] if len(buf) > overlap else ""

    for page_no, text in pages:
        for line in (l.strip() for l in text.splitlines()):
            if not line:
                continue
            if HEADING.match(line) and len(line) < 90 and not line.endswith((".", ",", ";")):
                flush()
                buf = ""
                section, buf_page = line, page_no
                continue
            if not buf:
                buf_page = page_no
            buf += line + " "
            if len(buf) >= target:
                flush()
    flush()
    return chunks


def _rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return scores


class PolicyIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray | None = None, embed_query=None):
        self.chunks = chunks
        self.vectors = vectors
        self.embed_query = embed_query
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None

    @property
    def mode(self) -> str:
        return "hybrid" if self.vectors is not None and self.embed_query else "bm25"

    def search(self, query: str, k: int = 4) -> list[Hit]:
        if not self.chunks or not self.bm25:
            return []
        pool = max(k * 3, 10)
        bm = self.bm25.get_scores(tokenize(query))
        bm_rank = [int(i) for i in np.argsort(-bm)[:pool] if bm[i] > 0]
        rankings = [bm_rank]
        vec_rank: list[int] = []
        if self.mode == "hybrid":
            try:
                q = np.asarray(self.embed_query(query), dtype=np.float32)
                q /= np.linalg.norm(q) + 1e-9
                sims = self.vectors @ q
                vec_rank = [int(i) for i in np.argsort(-sims)[:pool]]
                rankings.append(vec_rank)
            except Exception:  # embedding API hiccup -> degrade gracefully to BM25
                pass
        fused = _rrf(rankings)
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        via = "hybrid" if vec_rank else "bm25"
        return [Hit(self.chunks[i], round(fused[i], 4), via) for i in top]


def format_hits(hits: list[Hit]) -> str:
    if not hits:
        return "No relevant policy passage found."
    return "\n\n".join(f"[p.{h.chunk.page} | {h.chunk.section}]\n{h.chunk.text}" for h in hits)


# ---------- build / load ----------
def build_index(pdf_path: Path, out_dir: Path, embed_docs=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks = chunk_pages(extract_pages(pdf_path))
    (out_dir / "chunks.json").write_text(json.dumps([asdict(c) for c in chunks]))
    vec_file = out_dir / "vectors.npy"
    if vec_file.exists():
        vec_file.unlink()
    if embed_docs and chunks:
        v = np.asarray(embed_docs([c.text for c in chunks]), dtype=np.float32)
        v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
        np.save(vec_file, v)
    return {"chunks": len(chunks), "vectors": vec_file.exists()}


def load_index(index_dir: Path = None, embed_query=None) -> PolicyIndex | None:
    index_dir = index_dir or settings.index_dir
    cf = index_dir / "chunks.json"
    if not cf.exists():
        return None
    chunks = [Chunk(**c) for c in json.loads(cf.read_text())]
    vf = index_dir / "vectors.npy"
    vectors = np.load(vf) if vf.exists() else None
    return PolicyIndex(chunks, vectors, embed_query if vectors is not None else None)
