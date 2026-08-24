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
    
    # 4B.4.1: Separate PUBLIC vs PRO candidate channels
    best_public_promo = None
    best_public_discount = 0.0
    
    best_pro_promo = None
    best_pro_discount = 0.0
    
    def add_candidate(promo_dict, discount_val, is_pro):
        nonlocal best_public_promo, best_public_discount, best_pro_promo, best_pro_discount
        if is_pro:
            if discount_val > best_pro_discount:
                best_pro_discount = discount_val
                best_pro_promo = promo_dict
        else:
            if discount_val > best_public_discount:
                best_public_discount = discount_val
                best_public_promo = promo_dict

    if bundle and bundle.get("deal"):
        for deal in bundle["deal"]:
            try:
                p_val = float(deal.get("promotion_value") or 0)
                u_cond = float(deal.get("units_condition") or 0)
            except (ValueError, TypeError):
                continue
            if p_val > 0 and u_cond > 0 and p_val > u_cond:
                d = (1 - (u_cond / p_val)) * 100.0
                is_pro = deal.get("is_pro_exclusive") or deal.get("is_prime_exclusive") or False
                cand = {
                    "type": "NxM",
                    "label": deal.get("label", f"{int(p_val)}x{int(u_cond)}"),
                    "p_val": p_val,
                    "u_cond": u_cond,
                    "is_pro_exclusive": is_pro,
                    "limit": deal.get("limit") or deal.get("limits") or None
                }
                add_candidate(cand, d, is_pro)

    if bundle and bundle.get("percentage_unit"):
        for deal in bundle["percentage_unit"]:
            try:
                p_val = float(deal.get("promotion_value") or 0)
                u_cond = float(deal.get("units_condition") or 0)
            except (ValueError, TypeError):
                continue
            if p_val > 0 and u_cond > 0:
                total_cost = (u_cond - 1) + (1.0 - (p_val / 100.0))
                d = (1 - (total_cost / u_cond)) * 100.0
                is_pro = deal.get("is_pro_exclusive") or deal.get("is_prime_exclusive") or False
                cand = {
                    "type": "PROGRESSIVE",
                    "label": deal.get("label", f"-{int(p_val)}% en la {int(u_cond)}ª u."),
                    "p_val": p_val,
                    "u_cond": u_cond,
                    "is_pro_exclusive": is_pro,
                    "limit": deal.get("limit") or deal.get("limits") or None
                }
                add_candidate(cand, d, is_pro)

    progressive_raw = None
    if bundle and bundle.get("progressive"):
        progressive_raw = bundle.get("progressive")
        # Treat unknown progressive as public candidate by default, but with 0 effective discount
        if best_public_discount == 0:
            best_public_promo = {
                "type": "PROGRESSIVE_UNKNOWN",
                "label": "Progressive Deal",
                "is_pro_exclusive": False,
                "p_val": 0,
                "u_cond": 0,
                "limit": None
            }

    # discount_effective MUST ONLY REFLECT PUBLIC DEALS
    discount_effective = 0.0
    
    if best_public_promo:
        discount_promo = best_public_discount
        
    if best_public_promo and (best_public_discount > discount_price or best_public_promo["type"] == "PROGRESSIVE_UNKNOWN"):
        discount_effective = best_public_discount
        discount_source = "bundle"
        promo_type = best_public_promo["type"]
        promo_label = best_public_promo["label"]
        if promo_type == "NxM":
            eff_real_price = best_public_promo["p_val"] * (real_price if real_price > 0 else raw_price)
            eff_price = best_public_promo["u_cond"] * raw_price
        elif promo_type == "PROGRESSIVE":
            eff_real_price = best_public_promo["u_cond"] * (real_price if real_price > 0 else raw_price)
            eff_price = ((best_public_promo["u_cond"] - 1) + (1.0 - (best_public_promo["p_val"]/100.0))) * (real_price if real_price > 0 else raw_price)
    else:
        discount_effective = discount_price
        if discount_price > 0:
            promo_type = "Direct"
            
    has_pro_offer = p.get("is_prime_exclusive") or p.get("is_pro_exclusive") or False
    if best_pro_promo:
        has_pro_offer = True
        
    pro_price = None
    if has_pro_offer and p.get("PrimeDiscount"):
        pro_price = raw_price - float(p.get("PrimeDiscount"))
        
    # Calculate pro_discount_effective
    pro_discount_effective = 0.0
    # Pro price discount vs real price
    if pro_price is not None and real_price > 0 and pro_price < real_price:
        pro_discount_effective = (1 - (pro_price / real_price)) * 100.0
        
    # If there is a pro bundle that beats the pro price direct discount
    if best_pro_promo and best_pro_discount > pro_discount_effective:
        pro_discount_effective = best_pro_discount

    # Commercial Extra metadata dict
    commercial_extra = {
        "has_pro_offer": has_pro_offer,
        "pro_price": round(pro_price, 2) if pro_price is not None else None,
        "pro_discount_effective": round(pro_discount_effective, 2) if pro_discount_effective > 0 else None,
        "progressive": progressive_raw,
        "limit": best_public_promo.get("limit") if best_public_promo else None,
        "bundle_promotion_value": best_public_promo.get("p_val") if best_public_promo else None,
        "bundle_units_condition": best_public_promo.get("u_cond") if best_public_promo else None,
        "pro_promo_type": best_pro_promo["type"] if best_pro_promo else ("Direct" if pro_price else None),
        "pro_promo_label": best_pro_promo["label"] if best_pro_promo else None
    }

    eff_price = round(eff_price, 2)
    eff_real_price = round(eff_real_price, 2)
    discount_effective = round(discount_effective, 2) if promo_type != "PROGRESSIVE_UNKNOWN" else None

    return discount_price, discount_promo, discount_effective, discount_source, promo_type, promo_label, eff_price, eff_real_price, commercial_extra
