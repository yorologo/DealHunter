import sqlite3
import json
import uuid
import datetime

class DealWatcher:
    def __init__(self, db_path, price_drop_threshold=10.0):
        self.db_path = db_path
        self.price_drop_threshold = price_drop_threshold
        self.conn = sqlite3.connect(db_path)
        
    def generate_event_key(self, event_type, store_id, product_id, run_id):
        return f"{event_type}_{store_id}_{product_id}_{run_id}"

    def process_run(self, run_id):
        c = self.conn.cursor()
        
        
        c.execute("SELECT started_at FROM runs WHERE run_id = ?", (run_id,))
        run_started_at = c.fetchone()[0]
        
        c.execute("SELECT DISTINCT store_id FROM observations WHERE run_id = ?", (run_id,))
        completed_stores = [r[0] for r in c.fetchall()]
        if not completed_stores:
            return []
            
        store_list_str = ",".join(f"'{s}'" for s in completed_stores)
        
        c.execute(f'''
            SELECT id, store_id, product_id, price, original_price, discount_effective, 
                   has_pro_offer, pro_price, pro_discount_effective, promotion_type, availability
            FROM observations 
            WHERE run_id = ?
        ''', (run_id,))
        
        curr_obs_rows = c.fetchall()
        curr_obs = {}
        for r in curr_obs_rows:
            curr_obs[(r[1], r[2])] = {
                'id': r[0], 'price': r[3], 'original_price': r[4], 'discount_effective': r[5],
                'has_pro_offer': r[6], 'pro_price': r[7], 'pro_discount_effective': r[8],
                'promotion_type': r[9], 'availability': r[10]
            }
            
        c.execute(f'''
            SELECT o.id, o.store_id, o.product_id, o.price, o.original_price, o.discount_effective, 
                   o.has_pro_offer, o.pro_price, o.pro_discount_effective, o.promotion_type, o.availability
            FROM observations o
            INNER JOIN (
                SELECT store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE store_id IN ({store_list_str}) AND run_id != ? AND timestamp < (SELECT started_at FROM runs WHERE run_id = ?)
                GROUP BY store_id, product_id
            ) prev ON o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
        ''', (run_id, run_id))
        
        prev_obs_rows = c.fetchall()
        prev_obs = {}
        for r in prev_obs_rows:
            prev_obs[(r[1], r[2])] = {
                'id': r[0], 'price': r[3], 'original_price': r[4], 'discount_effective': r[5],
                'has_pro_offer': r[6], 'pro_price': r[7], 'pro_discount_effective': r[8],
                'promotion_type': r[9], 'availability': r[10]
            }
            
        # Get the latest state for products in these stores to prevent spam
        # We only care about OUT_OF_STOCK and BACK_IN_STOCK to know the current 'missing' state
        c.execute(f'''
            SELECT store_id, product_id, event_type
            FROM alert_events 
            WHERE store_id IN ({store_list_str}) 
              AND event_type IN ('OUT_OF_STOCK', 'BACK_IN_STOCK')
              AND created_at < (SELECT started_at FROM runs WHERE run_id = ?)
            ORDER BY created_at ASC
        ''', (run_id,))
        
        # This gives us the chronological sequence, so the last one is the current state
        state_history = {}
        for r in c.fetchall():
            state_history[(r[0], r[1])] = r[2]
        
        events = []
        
        def add_event(event_type, store_id, product_id, prev_id, curr_id, channel, before, after, meta):
            key = self.generate_event_key(event_type, store_id, product_id, run_id)
            events.append({
                'event_key': key,
                'event_type': event_type,
                'store_id': store_id,
                'product_id': product_id,
                'previous_observation_id': prev_id,
                'current_observation_id': curr_id,
                'channel': channel,
                'before_value': str(before) if before is not None else None,
                'after_value': str(after) if after is not None else None,
                'metadata': json.dumps(meta) if meta else None,
                'created_at': run_started_at
            })
            
        for (store_id, product_id), curr in curr_obs.items():
            prev = prev_obs.get((store_id, product_id))
            last_event = state_history.get((store_id, product_id))
            is_missing = (last_event == 'OUT_OF_STOCK')
            
            if not prev:
                if curr['discount_effective'] and curr['discount_effective'] >= 50:
                    add_event('NEW_PRODUCT_WITH_DEAL', store_id, product_id, None, curr['id'], 'PUBLIC', None, curr['discount_effective'], {'reason': 'newly observed >=50%'})
                continue
                
            if prev['availability'] == 'UNAVAILABLE' or is_missing:
                if curr['availability'] == 'AVAILABLE':
                    add_event('BACK_IN_STOCK', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', 'UNAVAILABLE', 'AVAILABLE', None)
                    is_missing = False # Now available for further evaluation
                else:
                    continue # Still unavailable, skip price checks
                    
            if curr['availability'] == 'UNAVAILABLE':
                continue
                
            if prev['price'] is not None and curr['price'] is not None and curr['price'] < prev['price']:
                drop_pct = (1 - curr['price'] / prev['price']) * 100
                if drop_pct >= self.price_drop_threshold:
                    add_event('PRICE_DROP', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev['price'], curr['price'], {'drop_pct': drop_pct})
                    
            prev_disc = prev['discount_effective'] or 0
            curr_disc = curr['discount_effective'] or 0
            if curr_disc > prev_disc:
                add_event('DISCOUNT_INCREASED', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_disc, curr_disc, None)
                if curr_disc >= 50 and prev_disc < 50:
                    add_event('NEW_DEAL', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_disc, curr_disc, {'reason': 'crossed 50%'})
                    
            prev_promo = prev['promotion_type'] or ''
            curr_promo = curr['promotion_type'] or ''
            if 'NxM' in curr_promo and 'NxM' not in prev_promo:
                add_event('NXM_APPEARED', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_promo, curr_promo, None)
                
            if 'Progressive' in curr_promo and 'Progressive' not in prev_promo:
                add_event('PROGRESSIVE_APPEARED', store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_promo, curr_promo, None)
                
            prev_pro = prev['has_pro_offer']
            curr_pro = curr['has_pro_offer']
            if curr_pro == 1 and prev_pro in (0, None):
                add_event('PRO_DEAL_APPEARED', store_id, product_id, prev['id'], curr['id'], 'PRO', prev_pro, curr_pro, {'pro_price': curr['pro_price'], 'pro_discount_effective': curr['pro_discount_effective']})

        for (store_id, product_id), prev in prev_obs.items():
            if (store_id, product_id) not in curr_obs:
                last_event = state_history.get((store_id, product_id))
                if prev['availability'] == 'AVAILABLE' and last_event != 'OUT_OF_STOCK':
                    add_event('OUT_OF_STOCK', store_id, product_id, prev['id'], None, 'PUBLIC', 'AVAILABLE', 'UNAVAILABLE', None)
                    
        final_events = []
        grouped = {}
        for ev in events:
            grouped.setdefault((ev['store_id'], ev['product_id']), []).append(ev)
            
        for key, evs in grouped.items():
            types = {e['event_type']: e for e in evs}
            
            if 'PRO_DEAL_APPEARED' in types:
                final_events.append(types['PRO_DEAL_APPEARED'])
                
            if 'OUT_OF_STOCK' in types:
                final_events.append(types['OUT_OF_STOCK'])
            if 'BACK_IN_STOCK' in types:
                final_events.append(types['BACK_IN_STOCK'])
                
            if 'NEW_PRODUCT_WITH_DEAL' in types:
                final_events.append(types['NEW_PRODUCT_WITH_DEAL'])
                
            if 'NEW_DEAL' in types:
                final_events.append(types['NEW_DEAL'])
                if 'NXM_APPEARED' in types:
                    final_events.append(types['NXM_APPEARED'])
                if 'PROGRESSIVE_APPEARED' in types:
                    final_events.append(types['PROGRESSIVE_APPEARED'])
            elif 'DISCOUNT_INCREASED' in types:
                final_events.append(types['DISCOUNT_INCREASED'])
                if 'NXM_APPEARED' in types:
                    final_events.append(types['NXM_APPEARED'])
                if 'PROGRESSIVE_APPEARED' in types:
                    final_events.append(types['PROGRESSIVE_APPEARED'])
            elif 'PRICE_DROP' in types:
                final_events.append(types['PRICE_DROP'])
            else:
                if 'NXM_APPEARED' in types and 'NEW_DEAL' not in types and 'DISCOUNT_INCREASED' not in types:
                    final_events.append(types['NXM_APPEARED'])
                if 'PROGRESSIVE_APPEARED' in types and 'NEW_DEAL' not in types and 'DISCOUNT_INCREASED' not in types:
                    final_events.append(types['PROGRESSIVE_APPEARED'])
                    
        return final_events

    def persist_events(self, events):
        c = self.conn.cursor()
        inserted = 0
        for ev in events:
            try:
                c.execute('''
                    INSERT INTO alert_events 
                    (event_key, event_type, store_id, product_id, previous_observation_id, 
                     current_observation_id, channel, before_value, after_value, metadata, created_at, delivery_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ev['event_key'], ev['event_type'], ev['store_id'], ev['product_id'],
                    ev['previous_observation_id'], ev['current_observation_id'],
                    ev['channel'], ev['before_value'], ev['after_value'],
                    ev['metadata'], ev['created_at'], 'pending'
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return inserted
