import statistics
from datetime import datetime, timedelta

def compute_price_metrics(obs_list):
    """
    obs_list: list of dicts with 'price', 'original_price', 'timestamp'
    ordered by timestamp ASC.
    """
    if not obs_list:
        return None
        
    current_obs = obs_list[-1]
    current_price = current_obs["price"]
    original_price = current_obs.get("original_price")
    
    if len(obs_list) > 1:
        previous_obs = obs_list[-2]
        previous_price = previous_obs["price"]
        prices_previous = [o["price"] for o in obs_list[:-1]]
        historical_min_previous = min(prices_previous)
    else:
        previous_price = current_price
        prices_previous = [current_price]
        historical_min_previous = current_price
        
    prices_all = [o["price"] for o in obs_list]
    historical_min = min(prices_all)
    historical_max = max(prices_all)
    historical_average = statistics.mean(prices_all)
    
    now = datetime.now()
    obs_30d = [o["price"] for o in obs_list if o["timestamp"] >= now - timedelta(days=30)]
    median_30d = statistics.median(obs_30d) if obs_30d else current_price
    
    price_change = current_price - previous_price
    price_change_percent = (price_change / previous_price * 100) if previous_price > 0 else 0
    
    discount_vs_median_30d = (1 - (current_price / median_30d)) * 100 if median_30d > 0 else 0
    discount_vs_historical_average = (1 - (current_price / historical_average)) * 100 if historical_average > 0 else 0
    distance_from_historical_min = ((current_price / historical_min) - 1) * 100 if historical_min > 0 else 0
    
    # Classify
    status = "NORMAL"
    reason = "Sin ventaja histórica demostrable"
    
    ts_min = obs_list[0]["timestamp"]
    ts_max = obs_list[-1]["timestamp"]
    delta_days = (ts_max - ts_min).total_seconds() / 86400.0
    
    # We require at least 3 observations AND spread over at least 24 hours to consider it has history
    if len(obs_list) < 3 or delta_days < 1.0:
        status = "INSUFFICIENT_HISTORY"
        reason = f"Historial insuficiente ({len(obs_list)} obs en {delta_days:.1f} dias)"
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
    if original_price and original_price > 0 and len(obs_list) >= 3:
        # If advertised original price is more than 20% higher than the historical max we've ever seen
        if original_price > historical_max * 1.2:
            is_suspicious = True
            if status != "INSUFFICIENT_HISTORY":
                # We can append or override reason
                reason += f" | SUSPICIOUS_REFERENCE_PRICE: Anunciado ${original_price} muy superior a max historico ${historical_max}"
                
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
        "history_days": (obs_list[-1]["timestamp"] - obs_list[0]["timestamp"]).days if len(obs_list) > 1 else 0
    }
