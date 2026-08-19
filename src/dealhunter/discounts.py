def calculate_discount(p):
    price = float(p.get("price") or 0)
    real_price = float(p.get("real_price") or 0)
    
    discount_price = 0.0
    if real_price > 0 and price < real_price:
        discount_price = (1 - (price / real_price)) * 100.0
        
    discount_promo = 0.0
    promo_type = ""
    promo_label = ""
    
    bundle = p.get("discounts_bundle", {})
    if bundle and bundle.get("deal"):
        deal = bundle["deal"][0]
        p_val = float(deal.get("promotion_value") or 0)
        u_cond = float(deal.get("units_condition") or 0)
        if p_val > 0 and u_cond > 0 and p_val > u_cond:
            discount_promo = (1 - (u_cond / p_val)) * 100.0
            promo_type = "NxM"
            promo_label = deal.get("label", f"{int(p_val)}x{int(u_cond)}")
            
    if discount_promo > discount_price:
        discount_effective = discount_promo
        discount_source = "bundle"
        eff_real_price = p_val * (real_price if real_price > 0 else price)
        eff_price = u_cond * price
    else:
        discount_effective = discount_price
        discount_source = "price"
        if discount_price > 0:
            promo_type = "Direct"
        eff_real_price = real_price
        eff_price = price
        
    return discount_price, discount_promo, discount_effective, discount_source, promo_type, promo_label, eff_price, eff_real_price
