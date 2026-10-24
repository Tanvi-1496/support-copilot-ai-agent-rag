"""Every query that depends on the exact column names lives here.
If your real blinkit.db uses different names, this is the only file to adjust
(the agents themselves read the live schema, so they adapt on their own)."""

ORDER = """
SELECT o.order_id, o.status, o.order_ts, o.promised_min, o.actual_min,
       (o.actual_min - o.promised_min) AS minutes_late, o.item_total, o.handling_fee, o.delivery_fee,
       o.surge_fee, o.gst, o.total, o.cancel_reason,
       c.name AS customer, c.tier AS customer_tier, ds.name AS dark_store, ci.name AS city
FROM orders o
JOIN customers c   ON c.customer_id = o.customer_id
JOIN dark_stores ds ON ds.store_id = o.store_id
JOIN cities ci     ON ci.city_id = ds.city_id
WHERE o.order_id = ?"""

ITEMS = """
SELECT oi.item_id, p.name AS product, oi.qty, oi.price, oi.item_status
FROM order_items oi JOIN products p ON p.product_id = oi.product_id
WHERE oi.order_id = ? ORDER BY oi.item_id"""

REFUNDS = """
SELECT refund_id, item_id, kind, amount, mode, status, reason, reject_reason, created_ts, completed_ts
FROM refunds WHERE order_id = ? ORDER BY refund_id"""

TICKETS = """
SELECT ticket_id, category, channel, stage, status, csat, created_ts
FROM support_tickets WHERE order_id = ? ORDER BY ticket_id"""

# ---- analytics (dashboard) ----
KPIS = {
    "orders": "SELECT COUNT(*) FROM orders",
    "delivered": "SELECT COUNT(*) FROM orders WHERE status='DELIVERED'",
    "late_pct": "SELECT ROUND(100.0*SUM(actual_min>promised_min)/COUNT(*),1) FROM orders WHERE status='DELIVERED'",
    "refund_total": "SELECT ROUND(COALESCE(SUM(amount),0)) FROM refunds WHERE status!='REJECTED'",
    "pending_count": "SELECT COUNT(*) FROM refunds WHERE status='PROCESSING'",
    "pending_amount": "SELECT ROUND(COALESCE(SUM(amount),0)) FROM refunds WHERE status='PROCESSING'",
    "avg_csat": "SELECT ROUND(AVG(csat),2) FROM support_tickets WHERE csat IS NOT NULL",
    "open_tickets": "SELECT COUNT(*) FROM support_tickets WHERE status!='RESOLVED'",
}

LATE_BY_CITY = """
SELECT ci.name AS city, COUNT(*) AS delivered,
       ROUND(100.0*SUM(o.actual_min>o.promised_min)/COUNT(*),1) AS late_pct
FROM orders o JOIN dark_stores ds ON ds.store_id=o.store_id JOIN cities ci ON ci.city_id=ds.city_id
WHERE o.status='DELIVERED' GROUP BY ci.name HAVING COUNT(*)>=30 ORDER BY late_pct DESC LIMIT 10"""

REFUNDS_BY_REASON = """
SELECT reason, COUNT(*) AS n, ROUND(SUM(amount)) AS amount
FROM refunds WHERE status!='REJECTED' GROUP BY reason ORDER BY amount DESC"""

REFUND_STATUS = "SELECT status, COUNT(*) AS n, ROUND(SUM(amount)) AS amount FROM refunds GROUP BY status ORDER BY n DESC"

MISSING_ITEMS = """
SELECT p.name AS product, COUNT(*) AS n
FROM order_items oi JOIN products p ON p.product_id=oi.product_id
WHERE oi.item_status='MISSING' GROUP BY p.name ORDER BY n DESC LIMIT 8"""

WORST_STORES = """
SELECT ds.name AS dark_store, ci.name AS city, COUNT(DISTINCT o.order_id) AS orders,
       COUNT(r.refund_id) AS refunds,
       ROUND(100.0*COUNT(r.refund_id)/COUNT(DISTINCT o.order_id),1) AS refunds_per_100_orders
FROM orders o JOIN dark_stores ds ON ds.store_id=o.store_id JOIN cities ci ON ci.city_id=ds.city_id
LEFT JOIN refunds r ON r.order_id=o.order_id
GROUP BY ds.store_id HAVING COUNT(DISTINCT o.order_id)>=30
ORDER BY refunds_per_100_orders DESC LIMIT 8"""

TIER_COMPARE = """
SELECT c.tier, COUNT(*) AS delivered,
       ROUND(AVG(o.actual_min),1) AS avg_minutes,
       ROUND(100.0*SUM(o.actual_min>o.promised_min)/COUNT(*),1) AS late_pct
FROM orders o JOIN customers c ON c.customer_id=o.customer_id
WHERE o.status='DELIVERED' GROUP BY c.tier"""
