from app import ops, tools


def test_order_summary_has_all_parts():
    text, ui = tools.get_order_summary({"order_id": 10245})
    assert ui["found"] and ui["late_by"] == 29 and ui["tier"] == "GOLD"
    assert "ITEMS" in text and "REFUNDS" in text and "LATE_DELIVERY" in text


def test_unknown_order():
    text, ui = tools.get_order_summary({"order_id": 99})
    assert ui["found"] is False


def test_sql_tool_blocks_writes():
    text, ui = tools.run_sql({"sql": "DELETE FROM refunds"})
    assert text.startswith("Rejected") and "error" in ui


def test_propose_action_only_queues():
    text, ui = tools.propose_action({"action": "WALLET_CREDIT", "order_id": 10245, "amount": 150, "reason": "Gold 29 min late (p.4)"})
    assert "NOT been executed" in text and ui["approval"]["status"] == "PENDING"
    assert any(a["id"] == ui["approval"]["id"] for a in ops.list_approvals("PENDING"))


def test_propose_action_limits():
    assert "error" in tools.propose_action({"action": "WALLET_CREDIT", "order_id": 1, "amount": 99999, "reason": "x"})[1]
    assert "error" in tools.propose_action({"action": "DELETE_REVIEWS", "order_id": 1, "amount": 0, "reason": "x"})[1]
