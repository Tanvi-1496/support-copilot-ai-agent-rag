"""Synthetic Blinkit-style data so the project runs end to end without the original files.
Not real Blinkit data. Replace data/blinkit.db and data/policy.pdf with your own and everything keeps working."""
from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE cities(city_id INTEGER PRIMARY KEY, name TEXT, tier INTEGER, zone TEXT, monsoon_flag INTEGER);
CREATE TABLE dark_stores(store_id INTEGER PRIMARY KEY, city_id INTEGER, name TEXT, avg_pick_pack_min REAL, sku_count INTEGER);
CREATE TABLE delivery_partners(partner_id INTEGER PRIMARY KEY, name TEXT, vehicle TEXT, rating REAL, city_id INTEGER);
CREATE TABLE customers(customer_id INTEGER PRIMARY KEY, name TEXT, tier TEXT, abuse_flag INTEGER, city_id INTEGER);
CREATE TABLE products(product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, mrp REAL, is_perishable INTEGER, is_weight_based INTEGER);
CREATE TABLE inventory(store_id INTEGER, product_id INTEGER, stock INTEGER, PRIMARY KEY(store_id, product_id));
CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER, store_id INTEGER, partner_id INTEGER, status TEXT,
  order_ts TEXT, promised_min INTEGER, actual_min INTEGER, item_total REAL, handling_fee REAL, delivery_fee REAL,
  surge_fee REAL, gst REAL, total REAL, cancel_reason TEXT);
CREATE TABLE order_items(item_id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, qty INTEGER, price REAL, item_status TEXT);
CREATE TABLE refunds(refund_id INTEGER PRIMARY KEY, order_id INTEGER, item_id INTEGER, kind TEXT, amount REAL, mode TEXT,
  status TEXT, reason TEXT, reject_reason TEXT, created_ts TEXT, completed_ts TEXT);
CREATE TABLE support_tickets(ticket_id INTEGER PRIMARY KEY, order_id INTEGER, customer_id INTEGER, category TEXT, channel TEXT,
  stage INTEGER, status TEXT, csat INTEGER, created_ts TEXT);
CREATE TABLE reviews(review_id INTEGER PRIMARY KEY, order_id INTEGER, delivery_rating INTEGER, product_rating INTEGER, text TEXT);
CREATE INDEX ix_orders_store ON orders(store_id); CREATE INDEX ix_items_order ON order_items(order_id);
CREATE INDEX ix_ref_order ON refunds(order_id); CREATE INDEX ix_tix_order ON support_tickets(order_id);
"""

CITIES = [("Mumbai", 1, "West", 1), ("Delhi", 1, "North", 0), ("Bengaluru", 1, "South", 0), ("Hyderabad", 1, "South", 0),
          ("Chennai", 1, "South", 1), ("Kolkata", 1, "East", 1), ("Pune", 1, "West", 1), ("Ahmedabad", 1, "West", 0),
          ("Jaipur", 2, "North", 0), ("Lucknow", 2, "North", 0), ("Coimbatore", 2, "South", 1), ("Kochi", 2, "South", 1),
          ("Vijayawada", 2, "South", 1), ("Nagpur", 2, "Central", 0), ("Indore", 2, "Central", 0), ("Surat", 2, "West", 1),
          ("Chandigarh", 2, "North", 0), ("Bhubaneswar", 2, "East", 1), ("Mysuru", 3, "South", 0), ("Madurai", 3, "South", 1),
          ("Nashik", 3, "West", 0), ("Vadodara", 3, "West", 0), ("Guwahati", 3, "East", 1), ("Dehradun", 3, "North", 0)]
PRODUCTS = [("Eggs (6 pack)", "Dairy & Eggs", 78, 1, 0), ("Full Cream Milk 500ml", "Dairy & Eggs", 33, 1, 0),
            ("Curd 400g", "Dairy & Eggs", 36, 1, 0), ("Paneer 200g", "Dairy & Eggs", 95, 1, 0),
            ("Lemon (4 pcs)", "Fruits & Vegetables", 24, 1, 0), ("Tomato (loose)", "Fruits & Vegetables", 40, 1, 1),
            ("Onion (loose)", "Fruits & Vegetables", 38, 1, 1), ("Potato (loose)", "Fruits & Vegetables", 32, 1, 1),
            ("Banana (loose)", "Fruits & Vegetables", 55, 1, 1), ("Coriander bunch", "Fruits & Vegetables", 15, 1, 0),
            ("Bread (white)", "Bakery", 45, 1, 0), ("Atta 5kg", "Staples", 260, 0, 0), ("Basmati Rice 1kg", "Staples", 140, 0, 0),
            ("Toor Dal 1kg", "Staples", 160, 0, 0), ("Sunflower Oil 1L", "Staples", 150, 0, 0), ("Maggi 4 pack", "Snacks", 56, 0, 0),
            ("Lays Classic", "Snacks", 20, 0, 0), ("Parle-G", "Snacks", 10, 0, 0), ("Coca-Cola 750ml", "Beverages", 40, 0, 0),
            ("Tata Tea 250g", "Beverages", 130, 0, 0), ("Dettol Handwash", "Household", 99, 0, 0), ("Surf Excel 1kg", "Household", 230, 0, 0),
            ("Marlboro Advance (pack)", "Age-restricted", 350, 0, 0), ("Ice Cream Tub", "Frozen", 180, 1, 0), ("Chicken Curry Cut 500g", "Meat", 210, 1, 1)]
FIRST = ["Aarav", "Diya", "Rohan", "Isha", "Kabir", "Meera", "Vivaan", "Ananya", "Arjun", "Sneha", "Rahul", "Pooja", "Karan",
         "Neha", "Siddharth", "Priya", "Aditya", "Kavya", "Manish", "Riya"]
LAST = ["Sharma", "Patel", "Nair", "Iyer", "Reddy", "Singh", "Gupta", "Das", "Mehta", "Joshi", "Kulkarni", "Verma"]


def make_db(path: Path, n_orders: int = 6000, seed: int = 7) -> None:
    rnd = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO cities VALUES(?,?,?,?,?)", [(i + 1, *c) for i, c in enumerate(CITIES)])
    stores = []
    for cid, (cname, tier, _, _) in enumerate(CITIES, start=1):
        for s in range(rnd.randint(3, 6)):
            stores.append((len(stores) + 1, cid, f"{cname} Dark Store {s + 1}", round(rnd.uniform(2.5, 6.5), 1), rnd.randint(2200, 4200)))
    con.executemany("INSERT INTO dark_stores VALUES(?,?,?,?,?)", stores)
    con.executemany("INSERT INTO delivery_partners VALUES(?,?,?,?,?)",
                    [(i, f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", rnd.choice(["BIKE", "EV", "SCOOTER"]),
                      round(rnd.uniform(3.6, 4.9), 1), rnd.randint(1, len(CITIES))) for i in range(1, 401)])
    custs = [(1, "Keerthana R.", "GOLD", 0, 11)]
    for i in range(2, 1501):
        custs.append((i, f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", "GOLD" if rnd.random() < 0.18 else "REGULAR",
                      1 if rnd.random() < 0.01 else 0, rnd.randint(1, len(CITIES))))
    con.executemany("INSERT INTO customers VALUES(?,?,?,?,?)", custs)
    con.executemany("INSERT INTO products VALUES(?,?,?,?,?,?)", [(i + 1, *p) for i, p in enumerate(PRODUCTS)])
    store_city = {s[0]: s[1] for s in stores}
    inv = [(s[0], p, 0 if rnd.random() < 0.06 else rnd.randint(3, 60)) for s in stores for p in range(1, len(PRODUCTS) + 1)]
    con.executemany("INSERT INTO inventory VALUES(?,?,?)", inv)

    city_info = {i + 1: c for i, c in enumerate(CITIES)}
    store_pick = {s[0]: s[3] for s in stores}
    base = datetime(2026, 7, 1, 8, 0)
    items_rows, ref_rows, tix_rows, rev_rows, orders = [], [], [], [], []
    iid = rid = tid = revid = 1
    bad_store = stores[12][0]  # one deliberately weak store so the analytics have a story

    def add_refund(oid, item_id, kind, amount, mode, status, reason, reject, created, completed):
        nonlocal rid
        ref_rows.append((rid, oid, item_id, kind, amount, mode, status, reason, reject, created, completed)); rid += 1

    for n in range(n_orders):
        oid = 10001 + n
        cust = 1 if oid == 10245 else rnd.randint(1, 1500)
        tier = custs[cust - 1][2]
        store = rnd.choice(stores)[0]
        city = city_info[store_city[store]]
        ts = base + timedelta(minutes=rnd.randint(0, 60 * 24 * 100))
        if oid == 10245:
            ts = datetime(2026, 8, 2, 20, 11)
        r = rnd.random()
        status = "DELIVERED" if r < 0.93 else ("CANCELLED" if r < 0.975 else "FAILED")
        late_p = 0.04 + (0.10 if city[3] else 0) + (0.02 if city[1] == 3 else 0) + (0.22 if store == bad_store else 0) + store_pick[store] * 0.006
        promised = 10
        actual = promised + (rnd.randint(2, 28) if rnd.random() < late_p else rnd.randint(-3, 0)) if status == "DELIVERED" else None
        k = rnd.randint(2, 6)
        chosen = rnd.sample(range(1, len(PRODUCTS) + 1), k)
        if oid == 10245:
            chosen = [3, 2, 11, 16]; actual = 39; status = "DELIVERED"
        item_total = 0
        cancel = None
        if status == "CANCELLED":
            cancel = rnd.choices(["STOCK_OUT", "CUSTOMER_REQUEST", "STORE_DELAY"], [5, 3, 1])[0]
        order_items = []
        for p in chosen:
            mrp = PRODUCTS[p - 1][2]; qty = rnd.randint(1, 2)
            st = "OK"
            if status == "DELIVERED":
                weights = [90, 4, 3, 1, 2] if not (store == bad_store) else [76, 10, 7, 3, 4]
                if p in (1, 5, 2): weights[1] += 4  # eggs, lemon, milk go missing more
                st = rnd.choices(["OK", "MISSING", "DAMAGED", "EXPIRED", "WEIGHT_SHORT"], weights)[0]
                if st == "WEIGHT_SHORT" and not PRODUCTS[p - 1][4]: st = "DAMAGED"
            if oid == 10245: st = "MISSING" if p == 3 else "OK"
            order_items.append((iid, oid, p, qty, mrp, st)); item_total += mrp * qty; iid += 1
        items_rows += order_items
        surge = rnd.choice([0, 0, 0, 10, 25]); handling = 4; delivery = rnd.choice([0, 15, 25, 35])
        gst = round((handling + delivery + surge) * 0.18, 2)
        orders.append((oid, cust, store, rnd.randint(1, 400), status, ts.strftime("%Y-%m-%d %H:%M"), promised, actual,
                       item_total, handling, delivery, surge, gst, round(item_total + handling + delivery + surge + gst, 2), cancel))
        # refunds
        for it in order_items:
            if it[5] != "OK":
                mode = rnd.choice(["WALLET", "UPI", "CARD"])
                done = rnd.random() < 0.93
                reject = None; stt = "COMPLETED" if done else "PROCESSING"
                if rnd.random() < 0.06:
                    stt, reject = "REJECTED", rnd.choice(["NO_PHOTO", "OUTSIDE_WINDOW", "WITHIN_TOLERANCE"])
                days = {"WALLET": 0, "UPI": rnd.randint(1, 3), "CARD": rnd.randint(3, 7)}[mode]
                created = ts + timedelta(hours=2)
                add_refund(oid, it[0], "ITEM", round(it[4] * it[3] * (0.3 if it[5] == "WEIGHT_SHORT" else 1), 2), mode, stt,
                           it[5], reject, created.strftime("%Y-%m-%d %H:%M"),
                           (created + timedelta(days=days)).strftime("%Y-%m-%d %H:%M") if stt == "COMPLETED" else None)
        if actual and actual - promised >= 15 and rnd.random() < 0.5:
            band = 150 if tier == "GOLD" else 75
            add_refund(oid, None, "ORDER", band, "WALLET", "PROCESSING" if rnd.random() < 0.25 else "COMPLETED", "LATE_DELIVERY", None,
                       (ts + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), None)
        if oid == 10245:  # the story used in the original session
            ref_rows[:] = [x for x in ref_rows if x[1] != oid]
            add_refund(oid, order_items[0][0], "ITEM", 36, "WALLET", "COMPLETED", "MISSING", None, "2026-08-02 20:40", "2026-08-02 20:40")
            add_refund(oid, None, "ORDER", 150, "UPI", "PROCESSING", "LATE_DELIVERY", None, "2026-08-02 21:10", None)
        if rnd.random() < 0.13 or oid == 10245:
            cat = rnd.choice(["MISSING_ITEM", "LATE_DELIVERY", "REFUND_DELAY", "RIDER_BEHAVIOUR", "PAYMENT", "QUALITY"])
            stg = rnd.choices([1, 2, 3], [80, 15, 5])[0]
            tix_rows.append((tid, oid, cust, cat, rnd.choice(["CHAT", "CALL", "EMAIL"]), stg,
                             rnd.choices(["RESOLVED", "OPEN", "ESCALATED"], [70, 20, 10])[0], rnd.choice([1, 2, 3, 3, 4, 4, 5, None]),
                             (ts + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"))); tid += 1
        if status == "DELIVERED" and rnd.random() < 0.3:
            rev_rows.append((revid, oid, rnd.choice([1, 2, 3, 4, 4, 5, 5]), rnd.choice([2, 3, 4, 5, 5]), "")); revid += 1

    con.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", orders)
    con.executemany("INSERT INTO order_items VALUES(?,?,?,?,?,?)", items_rows)
    con.executemany("INSERT INTO refunds VALUES(?,?,?,?,?,?,?,?,?,?,?)", ref_rows)
    con.executemany("INSERT INTO support_tickets VALUES(?,?,?,?,?,?,?,?,?)", tix_rows)
    con.executemany("INSERT INTO reviews VALUES(?,?,?,?,?)", rev_rows)
    con.commit(); con.close()


POLICY = [
    ("1. Ordering and the 10-minute promise", [
        "Blinkit fulfils orders from nearby dark stores. Pickers pack the order and a delivery partner brings it to the door. "
        "The promised delivery time shown at checkout is 10 minutes for most orders in serviced areas.",
        "An order counts as late when the actual delivery time is more than the promised time shown at checkout. "
        "Lateness is measured in whole minutes from order confirmation to handover."]),
    ("2. Fees and charges", [
        "A bill can contain an item total, a handling fee, a delivery fee, a surge fee during rain, peak demand or late night, and GST. "
        "GST is charged on the handling, delivery and surge fees. Fees are not refunded when a customer cancels after packing has started.",
        "Gold members get free delivery on orders above INR 199 and a reduced handling fee."]),
    ("3. Cancellation", [
        "A customer can cancel free of charge within 60 seconds of placing the order. After 60 seconds but before packing starts, "
        "the item total is refunded and fees are retained.",
        "If the store has started packing perishable items, the customer pays up to 100 percent of the perishable item total. "
        "Fees are not refunded after packing begins. If Blinkit cancels because of a stock-out, the full amount including fees is refunded."]),
    ("4. Item-level refunds", [
        "Blinkit refunds per item, not per order. An item can be MISSING, DAMAGED, EXPIRED or WEIGHT_SHORT. "
        "Report the problem in the app within 24 hours of delivery.",
        "A photo is required for DAMAGED and EXPIRED items. A photo is not required for MISSING items. "
        "For weight-based items such as loose vegetables, a tolerance of 10 percent applies. Beyond 10 percent a proportional refund is paid, "
        "and the customer must send a photo of the item on a scale.",
        "A refund can be rejected with the reason NO_PHOTO, OUTSIDE_WINDOW or WITHIN_TOLERANCE."]),
    ("5. Refund timelines", [
        "Wallet refunds are instant. UPI refunds reach the account in 1 to 3 working days. Card refunds take 3 to 5 working days. "
        "A refund pending beyond 5 working days is a breach of this policy and must be escalated.",
        "Fees are refunded only where this policy says so."]),
    ("6. Late delivery goodwill credit", [
        "When an order is delivered late, a goodwill credit is paid to the wallet. The amount depends on minutes late and membership tier. "
        "Late by 5 to 14 minutes: Regular INR 0, Gold INR 25. Late by 15 to 24 minutes: Regular INR 50, Gold INR 100. "
        "Late by 25 to 39 minutes: Regular INR 75, Gold INR 150. Late by 40 minutes or more: Regular INR 100, Gold INR 200.",
        "Goodwill credit is paid once per order. It is in addition to any item-level refund."]),
    ("7. Escalation", [
        "Stage 1 is the support team and responds within 48 hours. Stage 2 is the escalation team and responds within 7 days. "
        "Stage 3 is the Grievance Officer and responds within 30 days. A customer may move to the next stage if the previous response is unsatisfactory."]),
    ("8. Age-restricted items", [
        "Cigarettes, tobacco and alcohol where permitted require age verification. The delivery partner must check photo ID at the door. "
        "These items are never left unattended at the door. If ID is not shown the order is returned to the store."]),
    ("9. Account conduct and prohibited actions", [
        "Customer reviews cannot be deleted or edited by Blinkit staff or dark store managers, whether positive or negative. "
        "Support agents must not remove reviews to improve a store rating.",
        "Decisions about a named delivery partner, such as suspension or termination, are made by a human in the partner operations team "
        "and must never be automated. Refunds above INR 2000 and any money movement require human approval.",
        "Accounts flagged for refund abuse may have refunds reviewed manually."]),
]


def make_policy_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    ss = getSampleStyleSheet()
    story = [Paragraph("Ordering, Delivery and Refunds Policy and FAQ", ss["Title"]),
             Paragraph("Demo policy document for the Support Copilot project. Replace with your own PDF.", ss["Italic"]), Spacer(1, 18)]
    for i, (h, paras) in enumerate(POLICY):
        story.append(Paragraph(h, ss["Heading2"]))
        for p in paras:
            story += [Paragraph(p, ss["BodyText"]), Spacer(1, 8)]
        if i % 3 == 2:
            story.append(PageBreak())
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=A4).build(story)


if __name__ == "__main__":
    from app.config import settings
    make_db(settings.db_path); make_policy_pdf(settings.pdf_path); print("demo data written to", settings.data_dir)
