def calculate_discount(p):
    raw_price = float(p.get("price") or 0)
    real_price = float(p.get("real_price") or 0)
    
    have_discount = p.get("have_discount")
    api_discount = p.get("discount")
    
    if api_discount is not None:
        api_discount = float(api_discount)
        if api_discount > 1.0:
            # Normalize to fraction if Rappi sent it as percentage (e.g. 30 instead of 0.3)
            api_discount = api_discount / 100.0
            
    eff_price = raw_price
    eff_real_price = real_price
    discount_source = "explicit"
    promo_type = ""
    promo_label = ""
    
    # Validation against glitch:
    if have_discount is False:
        # Contract: if have_discount is strictly False, there is no discount, regardless of raw_price.
        eff_price = real_price
        discount_source = "none"
    elif api_discount and api_discount > 0 and real_price > 0:
        expected_price = real_price * (1.0 - api_discount)
        # Check if raw_price matches expected_price (within a reasonable rounding margin like 1.5 units)
        if abs(raw_price - expected_price) > 2.0:
            # Mismatch detected (e.g. 6.18 vs 58.5).
            # The raw_price is likely corrupted by a currency glitch. We rebuild it from the contract fields.
            eff_price = expected_price
            discount_source = "reconstructed"
        else:
            # We trust raw_price explicitly as it matches the contract.
            eff_price = raw_price
            discount_source = "explicit"

    # Now calculate effective discount from the validated prices
    discount_price = 0.0
    if eff_real_price > 0 and eff_price < eff_real_price:
        discount_price = (1 - (eff_price / eff_real_price)) * 100.0
        
    discount_promo = 0.0
    
    bundle = p.get("discounts_bundle", {})
    if bundle and bundle.get("deal"):
        deal = bundle["deal"][0]
        p_val = float(deal.get("promotion_value") or 0)
        u_cond = float(deal.get("units_condition") or 0)
        if p_val > 0 and u_cond > 0 and p_val > u_cond:
            discount_promo = (1 - (u_cond / p_val)) * 100.0
            
    if discount_promo > discount_price:
        discount_effective = discount_promo
        discount_source = "bundle"
        promo_type = "NxM"
        promo_label = deal.get("label", f"{int(p_val)}x{int(u_cond)}")
        eff_real_price = p_val * (real_price if real_price > 0 else raw_price)
        eff_price = u_cond * raw_price
    else:
        discount_effective = discount_price
        if discount_price > 0:
            promo_type = "Direct"
            
    # Rounding to 2 decimals for monetary representation consistency
    eff_price = round(eff_price, 2)
    eff_real_price = round(eff_real_price, 2)
    discount_effective = round(discount_effective, 2)

    return discount_price, discount_promo, discount_effective, discount_source, promo_type, promo_label, eff_price, eff_real_price
