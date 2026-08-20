def calculate_deal_score(metrics, current_price, original_price=None, market_min_price=None, store_count=1):
    """
    Calculates an explainable Deal Score (0-100).
    
    Components (Max 100):
    1. History Value (max 35) - Based on discount vs median_30d.
    2. Promo Value (max 20) - Based on original vs current (if not suspicious).
    3. Timing / Event (max 15) - Bonus for NEW_LOW, REAL_DEAL, etc.
    4. Market Position (max 20) - Bonus if it's the best price among stores.
    5. Evidence Quality (max 10) - Based on observation count and status.
    
    Returns a dict with score, label, confidence, and reasons.
    """
    score = 0
    reasons = []
    
    if not metrics:
        return {
            "score": 0, "label": "Sin historial", "confidence": "baja",
            "reasons": [{"type": "missing", "text": "Sin datos suficientes para evaluar"}]
        }
        
    status = metrics.get("deal_status", metrics.get("status", "NORMAL"))
    obs_count = metrics.get("observations_count", 0)
    
    # 1. Evidence Quality (0 - 10)
    evidence_score = 0
    confidence = "media"
    if status == "INSUFFICIENT_HISTORY":
        evidence_score = 2
        confidence = "baja"
    elif obs_count > 10:
        evidence_score = 10
        confidence = "alta"
    elif obs_count > 5:
        evidence_score = 7
    else:
        evidence_score = 4
        
    score += evidence_score
    
    # 2. History Value (0 - 35)
    hist_score = 0
    disc_vs_median = metrics.get("discount_vs_median_30d", 0) or 0
    if disc_vs_median > 0:
        # 1 point per percent, up to 35
        hist_score = min(35, int(disc_vs_median))
        score += hist_score
        reasons.append({"type": "history", "text": f"{disc_vs_median:.0f}% debajo de la mediana histórica"})
        
    # 3. Promo Value (0 - 20)
    promo_score = 0
    is_suspicious = metrics.get("is_suspicious_reference", False)
    if original_price and current_price < original_price:
        if is_suspicious:
            reasons.append({"type": "suspicious", "text": "⚠ Descuento promocional descartado (precio original atípico)"})
        else:
            disc_percent = ((original_price - current_price) / original_price) * 100
            promo_score = min(20, int(disc_percent))
            score += promo_score
            reasons.append({"type": "promo", "text": f"{disc_percent:.0f}% de descuento real comprobado"})
            
    # 4. Timing / Event (0 - 15)
    timing_score = 0
    if status == "NEW_LOW":
        timing_score = 15
        reasons.append({"type": "event", "text": "Nuevo mínimo histórico registrado"})
    elif status == "REAL_DEAL":
        timing_score = 10
        reasons.append({"type": "event", "text": "Caída de precio significativa"})
    elif status == "PRICE_DROP" or status == "GOOD_PRICE":
        timing_score = 5
    score += timing_score
    
    # 5. Market Position (0 - 20)
    market_score = 0
    if market_min_price is not None and store_count > 1:
        if current_price <= market_min_price:
            market_score = 20
            reasons.append({"type": "market", "text": f"Mejor precio entre {store_count} tiendas equivalentes"})
        else:
            # How far from the best?
            diff_percent = ((current_price - market_min_price) / market_min_price) * 100
            if diff_percent < 5:
                market_score = 10
            elif diff_percent < 10:
                market_score = 5
            # Otherwise 0
            if market_score > 0:
                reasons.append({"type": "market", "text": f"Precio muy competitivo ({store_count} tiendas equivalentes)"})
    elif store_count == 1:
        # If no equivalents, give a neutral baseline so it doesn't lose completely
        # (Assuming we have high evidence)
        if evidence_score >= 7:
            market_score = 10 
        else:
            market_score = 5
    score += market_score
    
    # Cap at 100
    score = min(100, max(0, score))
    
    # Labeling
    if score >= 90:
        label = "🔥 Excepcional"
    elif score >= 80:
        label = "🟢 Excelente"
    elif score >= 70:
        label = "👍 Buena compra"
    elif score >= 60:
        label = "🟡 Interesante"
    else:
        label = "Normal"
        
    return {
        "score": score,
        "label": label,
        "confidence": confidence,
        "reasons": reasons,
        "breakdown": {
            "evidence": f"{evidence_score}/10",
            "history": f"{hist_score}/35",
            "promo": f"{promo_score}/20",
            "timing": f"{timing_score}/15",
            "market": f"{market_score}/20"
        }
    }
