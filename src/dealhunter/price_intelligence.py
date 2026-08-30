import statistics
from datetime import datetime, timedelta
import math

def is_valid_commercial_price(price):
    if price is None:
        return False
    try:
        price_f = float(price)
        if math.isnan(price_f) or math.isinf(price_f):
            return False
        return price_f > 0
    except (TypeError, ValueError):
        return False


_EPOCH = datetime(1970, 1, 1)


def _safe_ts(obs):
    """Return the observation timestamp or epoch if None."""
    ts = obs.get("timestamp")
    return ts if ts is not None else _EPOCH


def compute_price_metrics(obs_list):
    """
    obs_list: list of dicts with 'price', 'original_price', 'timestamp'
    ordered by timestamp ASC.

    Observations whose price is None are excluded from all numeric
    calculations (they represent missing data, NOT zero).
    """
    if not obs_list:
        return None

    # Find the most recent valid observation to act as the current one
    valid_obs_list = [o for o in obs_list if is_valid_commercial_price(o["price"])]
    if not valid_obs_list:
        return None
        
    current_obs = valid_obs_list[-1]
    current_price = current_obs["price"]
    original_price = current_obs.get("original_price")

    # Build list of *valid* (non-None) prices for the full history.
    prices_all = [o["price"] for o in obs_list if is_valid_commercial_price(o["price"])]
    if not prices_all:
        return None

    # Previous price: walk backwards to find the most recent valid price
    # before the current observation.
    previous_price = current_price
    prices_previous = [o["price"] for o in valid_obs_list[:-1]]
    if prices_previous:
        previous_price = prices_previous[-1]

    historical_min_previous = min(prices_previous) if prices_previous else current_price
    historical_min = min(prices_all)
    historical_max = max(prices_all)
    historical_average = statistics.mean(prices_all)

    now = datetime.now()
    obs_30d = [o["price"] for o in obs_list
               if is_valid_commercial_price(o["price"]) and _safe_ts(o) >= now - timedelta(days=30)]
    median_30d = statistics.median(obs_30d) if obs_30d else current_price

    price_change = current_price - previous_price
    price_change_percent = (price_change / previous_price * 100) if previous_price and is_valid_commercial_price(previous_price) else 0

    discount_vs_median_30d = (1 - (current_price / median_30d)) * 100 if median_30d and is_valid_commercial_price(median_30d) else 0
    discount_vs_historical_average = (1 - (current_price / historical_average)) * 100 if historical_average and is_valid_commercial_price(historical_average) else 0
    distance_from_historical_min = ((current_price / historical_min) - 1) * 100 if historical_min and is_valid_commercial_price(historical_min) else 0

    # Classify
    status = "NORMAL"
    reason = "Sin ventaja histórica demostrable"

    ts_min = _safe_ts(obs_list[0])
    ts_max = _safe_ts(obs_list[-1])
    delta_days = (ts_max - ts_min).total_seconds() / 86400.0

    # Count observations with valid prices for history depth check
    valid_count = len(prices_all)

    # We require at least 3 *valid* observations AND spread over at least 24 hours to consider it has history
    if valid_count < 3 or delta_days < 1.0:
        status = "INSUFFICIENT_HISTORY"
        reason = f"Historial insuficiente ({valid_count} obs en {delta_days:.1f} dias)"
    else:
        if current_price < historical_min_previous:
            status = "NEW_LOW"
            reason = f"Nuevo mínimo histórico: ${current_price} (anterior: ${historical_min_previous})"
        elif discount_vs_median_30d >= 15.0:
            status = "REAL_DEAL"
            reason = f"Precio claramente inferior: {discount_vs_median_30d:.1f}% vs mediana 30d (${median_30d})"
        elif discount_vs_median_30d >= 5.0:
            status = "GOOD_PRICE"
            reason = f"Precio moderadamente inferior: {discount_vs_median_30d:.1f}% vs mediana 30d (${median_30d})"

    # Suspicious reference price check
    is_suspicious = False
    if original_price and original_price > 0 and valid_count >= 3:
        # If advertised original price is more than 20% higher than the historical max we've ever seen
        if original_price > historical_max * 1.2:
            is_suspicious = True
            if status != "INSUFFICIENT_HISTORY":
                # We can append or override reason
                reason += f" | SUSPICIOUS_REFERENCE_PRICE: Anunciado ${original_price} muy superior a max historico ${historical_max}"

    ts_first = _safe_ts(obs_list[0])
    ts_last = _safe_ts(obs_list[-1])

    return {
        "current_price": current_price,
        "original_price": original_price,
        "historical_min": historical_min,
        "historical_max": historical_max,
        "historical_average": historical_average,
        "median_30d": median_30d,
        "previous_price": previous_price,
        "price_change": price_change,
        "price_change_percent": price_change_percent,
        "discount_vs_median_30d": discount_vs_median_30d,
        "discount_vs_historical_average": discount_vs_historical_average,
        "distance_from_historical_min": distance_from_historical_min,
        "status": status,
        "reason": reason,
        "is_suspicious_reference": is_suspicious,
        "observations_count": len(obs_list),
        "history_days": (ts_last - ts_first).days if len(obs_list) > 1 else 0
    }

def compare_eligible_offers(canonical_product, provider_offers, membership_context=None):
    """
    Experimental 5H: Cross-Provider Deal Scoring.
    canonical_product: dict with canonical identity
    provider_offers: list of current valid offers from different providers
    membership_context: dict with eligibility status (e.g. {'rappi_pro': True, 'uber_one': False})
    
    Returns best offer and ranking.
    """
    if not provider_offers:
        return None
        
    membership_context = membership_context or {}
    scored_offers = []
    
    for offer in provider_offers:
        provider = offer.get("provider")
        raw_price = offer.get("price")
        if not is_valid_commercial_price(raw_price):
            continue
            
        # Membership eligibility
        eligible_price = raw_price
        member_price = offer.get("member_price")
        if member_price and member_price > 0 and member_price < raw_price:
            if provider == "rappi" and membership_context.get("rappi_pro"):
                eligible_price = member_price
            elif provider == "uber_eats" and membership_context.get("uber_one"):
                eligible_price = member_price
                
        # We can calculate unit price using canonical_product.quantity and canonical_product.unit
        qty = offer.get("quantity") or canonical_product.get("quantity")
        unit = offer.get("unit") or canonical_product.get("unit")
        
        unit_price = eligible_price
        if qty and qty > 0.0:
            unit_price = eligible_price / qty
            
        scored_offers.append({
            "provider": provider,
            "store_id": offer.get("store_id"),
            "product_id": offer.get("product_id"),
            "original_price": offer.get("original_price"),
            "raw_price": raw_price,
            "eligible_price": eligible_price,
            "unit_price": unit_price,
            "unit": unit
        })
        
    if not scored_offers:
        return None
        
    scored_offers.sort(key=lambda x: x["eligible_price"])
    best_offer = scored_offers[0]
    
    return {
        "best_offer": best_offer,
        "ranking": scored_offers,
        "spread_percent": ((scored_offers[-1]["eligible_price"] / best_offer["eligible_price"]) - 1) * 100 if is_valid_commercial_price(best_offer["eligible_price"]) else 0
    }
