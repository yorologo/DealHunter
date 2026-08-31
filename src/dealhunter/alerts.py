import sqlite3
from datetime import datetime
from .db import setup_db
from .historico import analyze_history

class AlertEngine:
    def __init__(self, db_path, config=None):
        self.db_path = db_path
        self.config = config or {}
        self.price_drop_percent = self.config.get("price_drop_percent", 10.0)
        self.conn = setup_db(db_path)
        
    def evaluate(self):
        """Evaluate all products and return new alerts."""
        c = self.conn.cursor()
        
        # 1. Fetch watchlist targets
        c.execute("SELECT query, store_filter, target_price FROM watchlist WHERE enabled = 1 AND target_price IS NOT NULL")
        targets = []
        for r in c.fetchall():
            targets.append({"query": r[0], "store": r[1], "target_price": r[2]})
            
        # 2. Get price intelligence metrics for ALL products
        metrics_by_product = analyze_history(self.db_path, {})
        
        # We need historical availability to check BACK_IN_STOCK. We'll fetch the last two observations for each product.
        c.execute('''
            SELECT provider, store_id, product_id, availability
            FROM trusted_observations
            ORDER BY timestamp ASC
        ''')
        avail_history = {}
        for r in c.fetchall():
            key = (r[0], r[1], r[2])
            if key not in avail_history:
                avail_history[key] = []
            avail_history[key].append(r[3])
            
        new_alerts = []
        
        for m in metrics_by_product:
            provider = m["provider"]
            store_id = m["store_id"]
            product_id = m["product_id"]
            product_name = m["product_name"]
            store_name = m["store_name"]
            current_price = m["current_price"]
            prev_price = m["previous_price"]
            status = m["deal_status"]
            
            # Check TARGET_PRICE
            for t in targets:
                if t["query"].lower() in product_name.lower():
                    if not t["store"] or t["store"] == store_id:
                        if current_price <= t["target_price"]:
                            self._try_add_alert(
                        new_alerts, provider, store_id, product_id, "TARGET_PRICE",
                                current_price, prev_price, status,
                                f"Precio actual ${current_price} <= objetivo ${t['target_price']}"
                            )
                            
            # Check NEW_LOW
            if status == "NEW_LOW":
                self._try_add_alert(
                        new_alerts, provider, store_id, product_id, "NEW_LOW",
                    current_price, prev_price, status,
                    m["reason"]
                )
                
            # Check REAL_DEAL
            if status == "REAL_DEAL":
                self._try_add_alert(
                        new_alerts, provider, store_id, product_id, "REAL_DEAL",
                    current_price, prev_price, status,
                    m["reason"]
                )
                
            # Check PRICE_DROP
            if prev_price > 0:
                drop_pct = (1 - (current_price / prev_price)) * 100
                if drop_pct >= self.price_drop_percent:
                    self._try_add_alert(
                        new_alerts, provider, store_id, product_id, "PRICE_DROP",
                        current_price, prev_price, status,
                        f"Precio bajó {drop_pct:.1f}% desde ${prev_price} a ${current_price}"
                    )
                    
            # Check BACK_IN_STOCK
            history = avail_history.get((provider, store_id, product_id), [])
            if len(history) >= 2:
                prev_avail = history[-2]
                curr_avail = history[-1]
                if prev_avail == "UNAVAILABLE" and curr_avail == "AVAILABLE":
                    self._try_add_alert(
                        new_alerts, provider, store_id, product_id, "BACK_IN_STOCK",
                        current_price, prev_price, status,
                        "Disponibilidad cambió de UNAVAILABLE a AVAILABLE"
                    )

        # Insert deduped alerts into DB
        c = self.conn.cursor()
        inserted_alerts = []
        for a in new_alerts:
            # Deduplication: we only insert if there isn't already an alert of the same type for this product
            # with the same or lower price (unless it's back in stock).
            # We'll use a simple rule: if the last alert of this type for this product had the same price, skip.
            # If the price dropped, allow a new alert.
            c.execute('''
                SELECT price FROM alerts
                WHERE provider = ? AND product_id = ? AND store_id = ? AND alert_type = ?
                ORDER BY triggered_at DESC LIMIT 1
            ''', (a["provider"], a["product_id"], a["store_id"], a["alert_type"]))
            row = c.fetchone()
            
            should_insert = True
            if row:
                last_price = row[0]
                if a["alert_type"] != "BACK_IN_STOCK" and a["price"] >= last_price:
                    should_insert = False
                elif a["alert_type"] == "BACK_IN_STOCK":
                    should_insert = False
                    
            if should_insert:
                now = datetime.now().isoformat()
                try:
                    c.execute('''
                        INSERT INTO alerts (provider, product_id, store_id, alert_type, triggered_at, price, previous_price, deal_status, reason, seen)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (a["provider"], a["product_id"], a["store_id"], a["alert_type"], now, a["price"], a["previous_price"], a["deal_status"], a["reason"]))
                    a["id"] = c.lastrowid
                    a["triggered_at"] = now
                    inserted_alerts.append(a)
                except sqlite3.IntegrityError:
                    pass # unique constraint hit (same exact everything)
                    
        self.conn.commit()
        return self.get_alerts(new_only=True)
        
    def _try_add_alert(self, alerts_list, provider, store_id, product_id, alert_type, price, previous_price, status, reason):
        alerts_list.append({
            "provider": provider,
            "store_id": store_id,
            "product_id": product_id,
            "alert_type": alert_type,
            "price": price,
            "previous_price": previous_price,
            "deal_status": status,
            "reason": reason
        })

    def get_alerts(self, new_only=False, top=50, status=None, store=None, alert_type=None):
        c = self.conn.cursor()
        
        query = '''
            SELECT a.id, a.alert_type, a.product_id, a.store_id, p.name, s.name, a.provider,
                   a.price, a.previous_price, a.deal_status, a.triggered_at, a.reason, a.seen
            FROM alerts a
            JOIN products p ON a.provider = p.provider AND a.product_id = p.product_id AND a.store_id = p.store_id
            JOIN stores s ON a.provider = s.provider AND a.store_id = s.store_id
            WHERE 1=1
        '''
        params = []
        
        if new_only:
            query += " AND a.seen = 0"
        if status:
            query += " AND a.deal_status = ?"
            params.append(status)
        if store:
            query += " AND a.store_id = ?"
            params.append(store)
        if alert_type:
            query += " AND a.alert_type = ?"
            params.append(alert_type)
            
        query += " ORDER BY a.triggered_at DESC LIMIT ?"
        params.append(top)
        
        c.execute(query, params)
        rows = c.fetchall()
        
        res = []
        for r in rows:
            res.append({
                "id": r[0],
                "alert_type": r[1],
                "product_id": r[2],
                "store_id": r[3],
                "product_name": r[4],
                "store_name": r[5],
                "provider": r[6],
                "current_price": r[7],
                "previous_price": r[8],
                "deal_status": r[9],
                "triggered_at": r[10],
                "reason": r[11],
                "seen": bool(r[12])
            })
        return res
        
    def mark_seen(self, alert_id=None, all=False):
        c = self.conn.cursor()
        if all:
            c.execute("UPDATE alerts SET seen = 1 WHERE seen = 0")
        elif alert_id:
            c.execute("UPDATE alerts SET seen = 1 WHERE id = ?", (alert_id,))
        self.conn.commit()
