"""Agent loop tested with a scripted fake model: no network, no API key."""
import pytest

from app import agents
from app.llm import Call, Step


@pytest.fixture(autouse=True)
def _restore_llm():
    real = agents.llm
    yield
    agents.llm = real


class FakeLLM:
    available = True

    def __init__(self, script):
        self.script, self.i = list(script), 0

    def start(self, history, question):
        return [("user", question)]

    def step(self, contents, system, tools=None, temperature=0.2):
        s = self.script[self.i]; self.i += 1
        return s

    def complete(self, prompt, system="", temperature=0.0):
        return self.step([], system)

    def add_tool_results(self, contents, step, results):
        contents.append(results)


def run(level, script, q="q", **kw):
    agents.llm = FakeLLM(script)
    return list(agents.run(level, q, [], **kw))


def types(evs):
    return [e["type"] for e in evs]


def test_agent_uses_tools_then_answers():
    evs = run("agent", [
        Step(calls=[Call("get_order_summary", {"order_id": 10245})]),
        Step(calls=[Call("policy_search", {"query": "gold goodwill 29 minutes"})]),
        Step(text="Gold member owed INR 150 (p.4)."),
    ])
    assert types(evs) == ["start", "tool_call", "tool_result", "tool_call", "tool_result", "final"]
    assert evs[-1]["tool_calls"] == 2 and "150" in evs[-1]["text"]
    assert evs[2]["ui"]["late_by"] == 29


def test_unknown_tool_does_not_crash():
    evs = run("agent", [Step(calls=[Call("hack_the_planet", {})]), Step(text="done")])
    assert evs[2]["ok"] is False and evs[-1]["type"] == "final"


def test_step_budget_forces_final_answer(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "agent_max_steps", 2)
    loop = [Step(calls=[Call("run_sql", {"sql": "SELECT 1"})])] * 2 + [Step(text="best effort")]
    evs = run("agent", loop)
    assert evs[-1]["type"] == "final" and evs[-1]["text"] == "best effort"


def test_supervisor_plans_delegates_and_merges():
    evs = run("agentic", [
        Step(calls=[Call("write_plan", {"steps": ["find drivers", "draft mail"]})]),
        Step(calls=[Call("delegate", {"agent": "quality-agent", "task": "late rate by city"})]),
        Step(calls=[Call("run_sql", {"sql": "SELECT COUNT(*) FROM orders"})]),   # inside quality-agent
        Step(text="Quality finding: X"),                                          # quality-agent answer
        Step(text="REPORT: X. Recommendations: ..."),                             # supervisor final
    ])
    t = types(evs)
    assert "plan" in t and "delegate" in t and "delegate_done" in t
    inner = [e for e in evs if e["type"] == "tool_call" and e["agent"] == "quality-agent"]
    assert len(inner) == 1 and evs[-1]["text"].startswith("REPORT")


def test_approval_event_emitted():
    evs = run("agent", [
        Step(calls=[Call("propose_action", {"action": "WALLET_CREDIT", "order_id": 10245, "amount": 150, "reason": "p.4"})]),
        Step(text="Queued for approval."),
    ])
    assert "approval" in types(evs)


def test_rag_policy_level():
    evs = run("rag", [Step(text="3 to 5 working days (p.2)")], q="card refund time", source="policy")
    assert types(evs) == ["start", "tool_call", "tool_result", "final"]
    assert evs[2]["ui"]["sources"]


def test_bad_level_and_empty_question():
    assert run("nope", [])[-1]["type"] == "error"
    assert run("llm", [], q="   ")[-1]["type"] == "error"


def test_supervisor_handles_unknown_worker():
    evs = run("agentic", [
        Step(calls=[Call("delegate", {"agent": "quantum-agent", "task": "solve physics"})]),
        Step(text="I understand the specialist was unavailable. Synthesizing available data."),
    ])
    done_ev = next(e for e in evs if e["type"] == "delegate_done")
    assert done_ev["ok"] is False
    assert "Unknown specialist agent" in done_ev["error"]
    assert evs[-1]["type"] == "final"


def test_supervisor_handles_empty_delegation_task():
    evs = run("agentic", [
        Step(calls=[Call("delegate", {"agent": "refund-agent", "task": "   "})]),
        Step(text="Task was empty, proceeding directly."),
    ])
    done_ev = next(e for e in evs if e["type"] == "delegate_done")
    assert done_ev["ok"] is False
    assert "without a specific task description" in done_ev["error"]
    assert evs[-1]["type"] == "final"


def test_write_plan_empty_and_list_handling():
    from app import tools
    _, ui_empty = tools.write_plan({"steps": []})
    assert ui_empty.get("error") == "empty plan"

    _, ui_str = tools.write_plan({"steps": "1. Check orders\n2. Run audit"})
    assert len(ui_str["steps"]) == 2
    assert ui_str["steps"][0] == "Check orders"


def test_agent_level3_does_not_have_delegation():
    """Confirms Level 3 is strictly a single-agent loop and does not have delegation tools."""
    from app import tools
    # Level 3 uses tools: get_order_summary, run_sql, policy_search, web_search, propose_action
    level3_names = {"get_order_summary", "run_sql", "policy_search", "web_search", "propose_action"}
    for name in level3_names:
        assert name in tools.TOOLS
    assert "delegate" not in tools.TOOLS
    assert "write_plan" not in level3_names
