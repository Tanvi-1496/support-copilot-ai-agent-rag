"""Dashboard numbers. Each block is isolated so one schema mismatch never blanks the whole page."""
from . import db, queries


def _safe(fn, default):
    try:
        return fn()
    except Exception as e:
        return default if not isinstance(default, dict) else {**default, "error": str(e)}


def overview() -> dict:
    kpis = {}
    for k, sql in queries.KPIS.items():
        kpis[k] = _safe(lambda s=sql: db.run_readonly(s)[1][0][0], None)
    return {
        "kpis": kpis,
        "late_by_city": _safe(lambda: db.rows_as_dicts(queries.LATE_BY_CITY), []),
        "refunds_by_reason": _safe(lambda: db.rows_as_dicts(queries.REFUNDS_BY_REASON), []),
        "refund_status": _safe(lambda: db.rows_as_dicts(queries.REFUND_STATUS), []),
        "missing_items": _safe(lambda: db.rows_as_dicts(queries.MISSING_ITEMS), []),
        "worst_stores": _safe(lambda: db.rows_as_dicts(queries.WORST_STORES), []),
        "tier_compare": _safe(lambda: db.rows_as_dicts(queries.TIER_COMPARE), []),
    }
