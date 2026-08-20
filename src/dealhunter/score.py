def calculate_deal_score(metrics, current_price, original_price=None, market_prices=None):
    """
    Calculates Deal Score (0-100) separating Deal Quality from Evidence Confidence.
    
    Confidence:
    - Alta: >= 10 observaciones Y >= 7 días de historial
    - Media: 3 - 9 observaciones Y >= 1 días de historial
    - Baja: < 3 observaciones O < 1 día de historial
    
    Score Components (Additive KISS model, Max 100):
    - Economic Discount (Max 60): Base deal quality. Max of (History vs Promo). 
    - Market Bonus (Max 30): Available only if market_equivalents > 1 and advantage > 0.
    - Timing Bonus (Max 10): NEW_LOW (+10), REAL_DEAL (+5).
    
    Missing Market does NOT inflate other components. It just yields 0 market bonus.
    """
    if not metrics:
        return {
            "score": 0, "label": "Sin historial", "confidence": "baja",
            "reasons": [{"type": "missing", "text": "Sin datos suficientes para evaluar"}],
            "breakdown": {}
        }
        
    # 1. CONFIDENCE
    obs_count = metrics.get("observations_count", 0)
    history_days = metrics.get("history_days", 0)
    
    if obs_count >= 10 and history_days >= 7:
        confidence = "alta"
    elif obs_count >= 3 and history_days >= 1:
        confidence = "media"
    else:
        confidence = "baja"
        
    # 2. SCORE COMPONENTS
    reasons = []
    
    # -- A. Economic Discount (0 - 60)
    discount_vs_median = metrics.get("discount_vs_median_30d", 0) or 0
    promo_discount = 0
    
    is_suspicious = metrics.get("is_suspicious_reference", False)
    if original_price and current_price < original_price:
        if is_suspicious:
            reasons.append({"type": "suspicious", "text": "⚠ Referencia promocional sospechosa (descartada)"})
        else:
            promo_discount = ((original_price - current_price) / original_price) * 100
            
    eff_discount = max(discount_vs_median, promo_discount)
    # Curve: 30% discount -> 60 pts.
    discount_score = min(60, int(eff_discount * 2.0))
    if discount_score < 0:
        discount_score = 0
    
    if eff_discount > 0:
        if eff_discount == discount_vs_median and discount_vs_median > 0:
            reasons.append({"type": "history", "text": f"↓ {discount_vs_median:.0f}% vs mediana 30d"})
        else:
            reasons.append({"type": "promo", "text": f"↓ {promo_discount:.0f}% de descuento comprobado"})
            
    # -- B. Market Bonus (0 - 30)
    market_score = 0
    market_available = False
    
    if market_prices and len(market_prices) > 1:
        market_available = True
        market_prices = sorted(market_prices)
        
        # Leader check
        if current_price <= market_prices[0]:
            # find second best (strict alternative)
            alt = next((p for p in market_prices if p > current_price), current_price)
            if alt > current_price:
                adv = ((alt - current_price) / alt) * 100
                # Curve: 15% cheaper than competition -> 30 pts
                market_score = min(30, int(adv * 2.0))
                if market_score > 0:
                    reasons.append({"type": "market", "text": f"🏆 {adv:.0f}% más barato que la competencia"})
            else:
                # Tied for leader -> +5 bonus
                market_score = 5
                reasons.append({"type": "market", "text": f"⚖ Mejor precio compartido ({len(market_prices)} tiendas)"})
        else:
            # We are not the leader
            market_score = 0
            reasons.append({"type": "market", "text": "⚠ Hay opciones más baratas en el mercado"})
            
    # -- C. Timing / Event (0 - 10)
    event_score = 0
    status = metrics.get("deal_status", metrics.get("status", "NORMAL"))
    if status == "NEW_LOW":
        event_score = 10
        reasons.append({"type": "event", "text": "🔥 Nuevo mínimo histórico"})
    elif status == "REAL_DEAL":
        event_score = 5
        reasons.append({"type": "event", "text": "💰 Caída de precio importante"})
    
    # 3. SCORE AGGREGATION
    score = discount_score + market_score + event_score
    score = min(100, max(0, score))
    
    # 4. LABELING (Capped by confidence)
    if score >= 90:
        label = "🔥 Excepcional" if confidence != "baja" else "👀 Prometedora"
    elif score >= 80:
        label = "🟢 Excelente" if confidence != "baja" else "👀 Prometedora"
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
        "reasons": reasons[:4],
        "breakdown": {
            "discount": f"{discount_score}/60",
            "market_available": market_available,
            "market": f"{market_score}/30",
            "event": f"{event_score}/10"
        }
    }
