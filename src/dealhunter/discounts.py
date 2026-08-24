def calculate_discount(p):
    raw_price = float(p.get("price") or 0)
    real_price = float(p.get("real_price") or 0)
    
    have_discount = p.get("have_discount")
    api_discount = p.get("discount")
    
    if api_discount is not None:
        api_discount = float(api_discount)
        if api_discount > 1.0:
            api_discount = api_discount / 100.0
            
    eff_price = raw_price
    eff_real_price = real_price
    discount_source = "explicit"
    promo_type = ""
    promo_label = ""
    
    if have_discount is False:
        eff_price = real_price
        discount_source = "none"
    elif api_discount and api_discount > 0 and real_price > 0:
        expected_price = real_price * (1.0 - api_discount)
        if abs(raw_price - expected_price) > 2.0:
            eff_price = expected_price
            discount_source = "reconstructed"
        else:
            eff_price = raw_price
            discount_source = "explicit"

    discount_price = 0.0
    if eff_real_price > 0 and eff_price < eff_real_price:
        discount_price = (1 - (eff_price / eff_real_price)) * 100.0
        
    discount_promo = 0.0
    
    bundle = p.get("discounts_bundle", {})
    # 14. MULTIPLE PROMOTIONS: evaluate all available promotions to find the best one order-independently.
    best_promo = None
    best_promo_discount = 0.0
    
    # Evaluate NxM deals
    if bundle and bundle.get("deal"):
        for deal in bundle["deal"]:
            p_val = float(deal.get("promotion_value") or 0)
            u_cond = float(deal.get("units_condition") or 0)
            if p_val > 0 and u_cond > 0 and p_val > u_cond:
                d = (1 - (u_cond / p_val)) * 100.0
                if d > best_promo_discount:
                    best_promo_discount = d
                    best_promo = {
                        "type": "NxM",
                        "label": deal.get("label", f"{int(p_val)}x{int(u_cond)}"),
                        "p_val": p_val,
                        "u_cond": u_cond,
                        "is_pro_exclusive": deal.get("is_pro_exclusive") or deal.get("is_prime_exclusive") or False,
                        "limit": deal.get("limit") or deal.get("limits") or None
                    }

    # Evaluate percentage_unit deals (e.g., "Segunda unidad -24%")
    if bundle and bundle.get("percentage_unit"):
        for deal in bundle["percentage_unit"]:
            p_val = float(deal.get("promotion_value") or 0) # e.g. 24
            u_cond = float(deal.get("units_condition") or 0) # e.g. 2 (second unit)
            if p_val > 0 and u_cond > 0:
                # Example: 2nd unit -24%. Total cost for 2 units = 1 + (1 - 0.24) = 1.76 units.
                # Effective discount = (1 - (1.76 / 2)) = 0.12 (12%)
                total_cost = (u_cond - 1) + (1.0 - (p_val / 100.0))
                d = (1 - (total_cost / u_cond)) * 100.0
                if d > best_promo_discount:
                    best_promo_discount = d
                    best_promo = {
                        "type": "PROGRESSIVE",
                        "label": deal.get("label", f"-{int(p_val)}% en la {int(u_cond)}ª u."),
                        "p_val": p_val,
                        "u_cond": u_cond,
                        "is_pro_exclusive": deal.get("is_pro_exclusive") or deal.get("is_prime_exclusive") or False,
                        "limit": deal.get("limit") or deal.get("limits") or None
                    }

    # Evaluate progressive explicitly if exists (fallback uncertain)
    progressive_raw = None
    if bundle and bundle.get("progressive"):
        progressive_raw = bundle.get("progressive")
        # Mark it as progressive but if we can't do the math, discount_effective = UNKNOWN (None).
        # We handle this by adding it to best_promo if we don't have a better one.
        if best_promo_discount == 0:
            best_promo = {
                "type": "PROGRESSIVE_UNKNOWN",
                "label": "Progressive Deal",
                "is_pro_exclusive": False,
                "p_val": 0,
                "u_cond": 0,
                "limit": None
            }

    if best_promo and (best_promo_discount > discount_price or best_promo["type"] == "PROGRESSIVE_UNKNOWN"):
        discount_promo = best_promo_discount
        discount_effective = discount_promo
        discount_source = "bundle"
        promo_type = best_promo["type"]
        promo_label = best_promo["label"]
        if promo_type == "NxM":
            eff_real_price = best_promo["p_val"] * (real_price if real_price > 0 else raw_price)
            eff_price = best_promo["u_cond"] * raw_price
        elif promo_type == "PROGRESSIVE":
            eff_real_price = best_promo["u_cond"] * (real_price if real_price > 0 else raw_price)
            eff_price = ((best_promo["u_cond"] - 1) + (1.0 - (best_promo["p_val"]/100.0))) * (real_price if real_price > 0 else raw_price)
    else:
        discount_effective = discount_price
        if discount_price > 0:
            promo_type = "Direct"
            
    is_pro = p.get("is_prime_exclusive") or p.get("is_pro_exclusive") or False
    if best_promo and best_promo.get("is_pro_exclusive"):
        is_pro = True
        
    pro_price = None
    if is_pro and p.get("PrimeDiscount"):
        pro_price = raw_price - float(p.get("PrimeDiscount"))

    # Commercial Extra metadata dict
    commercial_extra = {
        "is_pro_exclusive": is_pro,
        "pro_price": pro_price,
        "progressive": progressive_raw,
        "limit": best_promo.get("limit") if best_promo else None,
        "bundle_promotion_value": best_promo.get("p_val") if best_promo else None,
        "bundle_units_condition": best_promo.get("u_cond") if best_promo else None
    }

    eff_price = round(eff_price, 2)
    eff_real_price = round(eff_real_price, 2)
    discount_effective = round(discount_effective, 2) if promo_type != "PROGRESSIVE_UNKNOWN" else None

    return discount_price, discount_promo, discount_effective, discount_source, promo_type, promo_label, eff_price, eff_real_price, commercial_extra
