"""Run: python -m evals.run_evals   (needs GOOGLE_API_KEY). Prints a pass/fail table and writes evals/last_run.json.
Checks: expected tools were used, answer contains expected facts, forbidden tools were not used."""
import json
import sys
import time
from pathlib import Path

from app import agents, tools
from app.config import settings
from app.llm import llm
from app.rag import load_index
from scripts.bootstrap import bootstrap


def main():
    if not llm.available:
        sys.exit("Set GOOGLE_API_KEY first.")
    bootstrap()
    tools.set_index(load_index(embed_query=llm.embed_query))
    cases = json.loads((Path(__file__).parent / "cases.json").read_text())
    rows, passed = [], 0
    for c in cases:
        used, text, err = [], "", None
        t0 = time.time()
        for ev in agents.run(c["level"], c["q"], [], c.get("source", "policy")):
            if ev["type"] == "tool_call":
                used.append(ev["name"])
            if ev["type"] == "final":
                text = ev["text"]
            if ev["type"] == "error":
                err = ev["message"]
        low = text.lower()
        needles = [n.lower() for n in c.get("contains", [])]
        ok_text = (not needles) or (any(n in low for n in needles) if c.get("any") else all(n in low for n in needles))
        ok_tools = all(t in used for t in c.get("tools", [])) and not any(t in used for t in c.get("forbid_tools", []))
        ok = ok_text and ok_tools and not err
        passed += ok
        rows.append({"id": c["id"], "level": c["level"], "pass": ok, "tools": used, "seconds": round(time.time() - t0, 1),
                     "error": err, "answer": text[:400]})
        print(f"{'PASS' if ok else 'FAIL'}  {c['id']:<26} {c['level']:<8} tools={used}")
    print(f"\n{passed}/{len(cases)} passed  (model: {settings.model})")
    (Path(__file__).parent / "last_run.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
