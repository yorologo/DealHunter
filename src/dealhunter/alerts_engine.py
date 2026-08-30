import sqlite3
import json
import uuid
import datetime
from dealhunter.eligibility import EligibilityEngine

class DealWatcher:
    def __init__(self, db_path, config=None, price_drop_threshold=10.0):
        self.db_path = db_path
        self.config = config or {}
        self.price_drop_threshold = price_drop_threshold
        self.conn = sqlite3.connect(db_path)

        
    def generate_event_key(self, event_type, provider, store_id, product_id, run_id):
        return f"{event_type}_{provider}_{store_id}_{product_id}_{run_id}"

    def process_run(self, run_id):
        c = self.conn.cursor()
        
        
        c.execute("SELECT started_at FROM runs WHERE run_id = ?", (run_id,))
        run_started_at = c.fetchone()[0]
        
        c.execute("SELECT DISTINCT provider, store_id FROM observations WHERE run_id = ?", (run_id,))
        completed_scopes = [(r[0], r[1]) for r in c.fetchall()]
        if not completed_scopes:
            return []

        scope_sql = " OR ".join("(provider = ? AND store_id = ?)" for _ in completed_scopes)
        scope_params = [value for scope in completed_scopes for value in scope]
        
        c.execute(f'''
            SELECT id, store_id, product_id, price, original_price, discount_effective, 
                   has_pro_offer, pro_price, pro_discount_effective, promotion_type, availability, provider
            FROM observations 
            WHERE run_id = ?
        ''', (run_id,))
        
        curr_obs_rows = c.fetchall()
        curr_obs = {}
        for r in curr_obs_rows:
            curr_obs[(r[11], r[1], r[2])] = {
                'id': r[0], 'price': r[3], 'original_price': r[4], 'discount_effective': r[5],
                'has_pro_offer': r[6], 'pro_price': r[7], 'pro_discount_effective': r[8],
                'promotion_type': r[9], 'availability': r[10], 'provider': r[11]
            }
            
        c.execute(f'''
            SELECT o.id, o.store_id, o.product_id, o.price, o.original_price, o.discount_effective, 
                   o.has_pro_offer, o.pro_price, o.pro_discount_effective, o.promotion_type, o.availability, o.provider
            FROM observations o
            INNER JOIN (
                SELECT provider, store_id, product_id, MAX(timestamp) as max_ts
                FROM observations
                WHERE ({scope_sql}) AND run_id != ? AND timestamp < (SELECT started_at FROM runs WHERE run_id = ?)
                GROUP BY provider, store_id, product_id
            ) prev ON o.provider = prev.provider AND o.store_id = prev.store_id AND o.product_id = prev.product_id AND o.timestamp = prev.max_ts
        ''', (*scope_params, run_id, run_id))
        
        prev_obs_rows = c.fetchall()
        prev_obs = {}
        for r in prev_obs_rows:
            prev_obs[(r[11], r[1], r[2])] = {
                'id': r[0], 'price': r[3], 'original_price': r[4], 'discount_effective': r[5],
                'has_pro_offer': r[6], 'pro_price': r[7], 'pro_discount_effective': r[8],
                'promotion_type': r[9], 'availability': r[10], 'provider': r[11]
            }
            
        # Get the latest state for products in these stores to prevent spam
        # We only care about OUT_OF_STOCK and BACK_IN_STOCK to know the current 'missing' state
        c.execute(f'''
            SELECT provider, store_id, product_id, event_type
            FROM alert_events 
            WHERE ({scope_sql})
              AND event_type IN ('OUT_OF_STOCK', 'BACK_IN_STOCK')
              AND created_at < (SELECT started_at FROM runs WHERE run_id = ?)
            ORDER BY created_at ASC
        ''', (*scope_params, run_id))
        
        # This gives us the chronological sequence, so the last one is the current state
        state_history = {}
        for r in c.fetchall():
            state_history[(r[0], r[1], r[2])] = r[3]
        
        events = []
        
        def add_event(event_type, provider, store_id, product_id, prev_id, curr_id, channel, before, after, meta):
            key = self.generate_event_key(event_type, provider, store_id, product_id, run_id)
            events.append({
                'event_key': key,
                'event_type': event_type,
                'store_id': store_id,
                'product_id': product_id,
                'provider': provider,
                'previous_observation_id': prev_id,
                'current_observation_id': curr_id,
                'channel': channel,
                'before_value': str(before) if before is not None else None,
                'after_value': str(after) if after is not None else None,
                'metadata': json.dumps(meta) if meta else None,
                'created_at': run_started_at
            })
            
        engine = EligibilityEngine(self.config)
        for (provider, store_id, product_id), curr in curr_obs.items():
            prev = prev_obs.get((provider, store_id, product_id))
            last_event = state_history.get((provider, store_id, product_id))
            is_missing = (last_event == 'OUT_OF_STOCK')
            curr_provider = curr['provider']
            
            if not prev:
                if curr['discount_effective'] and curr['discount_effective'] >= 50:
                    add_event('NEW_PRODUCT_WITH_DEAL', provider, store_id, product_id, None, curr['id'], 'PUBLIC', None, curr['discount_effective'], {'reason': 'newly observed >=50%'})
                continue
                
            if prev['availability'] == 'UNAVAILABLE' or is_missing:
                if curr['availability'] == 'AVAILABLE':
                    add_event('BACK_IN_STOCK', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', 'UNAVAILABLE', 'AVAILABLE', None)
                    is_missing = False # Now available for further evaluation
                else:
                    continue # Still unavailable, skip price checks
                    
            if curr['availability'] == 'UNAVAILABLE':
                continue
                
            if prev['price'] is not None and curr['price'] is not None and curr['price'] < prev['price']:
                drop_pct = (1 - curr['price'] / prev['price']) * 100
                if drop_pct >= self.price_drop_threshold:
                    add_event('PRICE_DROP', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev['price'], curr['price'], {'drop_pct': drop_pct})
                    
            prev_disc = prev['discount_effective'] or 0
            curr_disc = curr['discount_effective'] or 0
            if curr_disc > prev_disc:
                add_event('DISCOUNT_INCREASED', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_disc, curr_disc, None)
                if curr_disc >= 50 and prev_disc < 50:
                    add_event('NEW_DEAL', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_disc, curr_disc, {'reason': 'crossed 50%'})
                    
            prev_promo = prev['promotion_type'] or ''
            curr_promo = curr['promotion_type'] or ''
            if 'NxM' in curr_promo and 'NxM' not in prev_promo:
                add_event('NXM_APPEARED', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_promo, curr_promo, None)
                
            if 'Progressive' in curr_promo and 'Progressive' not in prev_promo:
                add_event('PROGRESSIVE_APPEARED', provider, store_id, product_id, prev['id'], curr['id'], 'PUBLIC', prev_promo, curr_promo, None)
                
            prev_pro = prev['has_pro_offer']
            curr_pro = curr['has_pro_offer']
            if curr_pro == 1 and prev_pro in (0, None):
                # Check eligibility
                elig = engine.evaluate(curr_provider, True)
                if elig["ranking_eligible"]:
                    meta = {'pro_price': curr['pro_price'], 'pro_discount_effective': curr['pro_discount_effective']}
                    req_mem = engine.map_offer_to_membership(curr_provider, True)
                    if req_mem != "NONE":
                        meta["requires_membership"] = req_mem
                        meta["membership_status"] = engine.get_membership_status(req_mem)
                    add_event('PRO_DEAL_APPEARED', provider, store_id, product_id, prev['id'], curr['id'], 'PRO', prev_pro, curr_pro, meta)

        for (provider, store_id, product_id), prev in prev_obs.items():
            if (provider, store_id, product_id) not in curr_obs:
                last_event = state_history.get((provider, store_id, product_id))
                if prev['availability'] == 'AVAILABLE' and last_event != 'OUT_OF_STOCK':
                    add_event('OUT_OF_STOCK', provider, store_id, product_id, prev['id'], None, 'PUBLIC', 'AVAILABLE', 'UNAVAILABLE', None)
                    
        final_events = []
        grouped = {}
        for ev in events:
            grouped.setdefault((ev.get('provider', 'rappi'), ev['store_id'], ev['product_id']), []).append(ev)
            
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
                    (provider, event_key, event_type, store_id, product_id, previous_observation_id,
                     current_observation_id, channel, before_value, after_value, metadata, created_at, delivery_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    ev['provider'], ev['event_key'], ev['event_type'], ev['store_id'], ev['product_id'],
                    ev['previous_observation_id'], ev['current_observation_id'],
                    ev['channel'], ev['before_value'], ev['after_value'],
                    ev['metadata'], ev['created_at'], 'pending'
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()
        return inserted
