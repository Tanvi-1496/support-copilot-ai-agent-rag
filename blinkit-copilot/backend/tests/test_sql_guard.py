import pytest
from app import db


def test_select_ok():
    cols, rows, _ = db.run_readonly("SELECT COUNT(*) AS n FROM orders")
    assert cols == ["n"] and rows[0][0] > 0


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders", "DROP TABLE orders", "UPDATE orders SET total=0",
    "INSERT INTO refunds(refund_id) VALUES(999999)", "SELECT 1; DROP TABLE orders",
    "PRAGMA writable_schema=1", "ATTACH DATABASE '/tmp/x.db' AS x", "", "   ;  ",
])
def test_writes_and_tricks_rejected(sql):
    with pytest.raises(Exception):
        db.run_readonly(sql)


def test_cte_allowed_and_limited():
    cols, rows, trunc = db.run_readonly("WITH t AS (SELECT * FROM order_items) SELECT * FROM t", limit=5)
    assert len(rows) == 5 and trunc


def test_runaway_query_is_killed(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "sql_timeout_s", 0.2)
    with pytest.raises(db.SQLRejected):
        db.run_readonly("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT COUNT(*) FROM c")


def test_schema_text_lists_tables():
    s = db.schema_text()
    assert "CREATE TABLE orders" in s and "refunds" in s
