from app import rag, tools


def test_chunks_have_pages_and_sections():
    idx = tools.get_index()
    assert idx and len(idx.chunks) >= 8
    assert all(c.page >= 1 and c.section for c in idx.chunks)


def test_retrieval_finds_right_policy():
    idx = tools.get_index()
    cases = {
        "how long does a card refund take": "3 to 5 working days",
        "free cancellation window": "60 seconds",
        "weight tolerance for loose vegetables": "10 percent",
        "gold goodwill credit 29 minutes late": "Gold INR 150",
        "can reviews be deleted": "cannot be deleted",
        "escalation stages response time": "48 hours",
    }
    for q, needle in cases.items():
        hits = idx.search(q, k=3)
        assert any(needle in h.chunk.text for h in hits), (q, [h.chunk.section for h in hits])


def test_rrf_prefers_docs_in_both_rankings():
    scores = rag._rrf([[1, 2, 3], [3, 1, 4]])
    assert scores[1] > scores[2] and scores[3] > scores[4]


def test_policy_tool_returns_page_tags():
    text, ui = tools.policy_search({"query": "refund timeline for UPI"})
    assert "[p." in text and ui["sources"]
