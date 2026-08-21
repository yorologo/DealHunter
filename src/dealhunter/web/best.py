from dealhunter.historico import analyze_history
from dealhunter.score import calculate_deal_score
from collections import defaultdict
import datetime

def get_best_buys(db_path, filters, sort, page, per_page=25):
    res = analyze_history(db_path, filters, None, None)
    
    # Filter out items that are essentially invalid for best buys
    # Example: no current price, etc.

    # Filter out items that are essentially invalid for best buys
    valid_res = []
    for r in res:
        if not r.get("current_price"): continue
        
        # apply category filter
        if filters.get("category"):
            cats = filters["category"]
            c = r.get("category") or "Uncategorized"
            if isinstance(cats, list) and cats:
                if c not in cats:
                    continue
            elif isinstance(cats, str) and cats:
                if c != cats:
                    continue
            
        # apply store_type filter
        if filters.get("store_type"):
            st = filters["store_type"]
            r_st = r.get("store_type")
            
            # Map turbo
            if st == "turbo":
                if r_st not in ("chiper_home", "chiper_extended", "chiper_express"):
                    continue
            elif st == "market":
                if r_st in ("chiper_home", "chiper_extended", "chiper_express", "restaurants"):
                    continue
            elif st == "restaurants":
                if r_st != "restaurants":
                    continue
            else:
                if r_st != st:
                    continue
        
        valid_res.append(r)

    
    fingerprint_prices = defaultdict(list)
    for r in valid_res:
        fp = r.get("fingerprint")
        if fp:
            fingerprint_prices[fp].append(r["current_price"])
            
    for r in valid_res:
        fp = r.get("fingerprint")
        market_prices = fingerprint_prices[fp] if fp else []
        score_data = calculate_deal_score(r, r["current_price"], r.get("original_price"), market_prices)
        r["score_data"] = score_data
        r["deal_score"] = score_data["score"]
        
        conf = score_data.get("confidence", "baja")
        r["confidence_rank"] = 3 if conf == "alta" else (2 if conf == "media" else 1)
        # Format for catalog_grid expects "metrics" with discount_percent and savings
        if "metrics" not in r:
            r["metrics"] = r.copy() # fallback
        if r.get("original_price") and r.get("current_price"):
            r["metrics"]["discount_percent"] = ((r["original_price"] - r["current_price"]) / r["original_price"]) * 100
            r["metrics"]["savings"] = r["original_price"] - r["current_price"]
        else:
            r["metrics"]["discount_percent"] = 0
            r["metrics"]["savings"] = 0
            
    # Sort
    if sort == "score":
        valid_res.sort(key=lambda x: (x["confidence_rank"], x["deal_score"], x.get("timestamp", ""), x["store_id"], x["product_id"]), reverse=True)
    elif sort == "discount":
        valid_res.sort(key=lambda x: (x["metrics"]["discount_percent"], x["deal_score"], x["store_id"], x["product_id"]), reverse=True)
    elif sort == "savings":
        valid_res.sort(key=lambda x: (x["metrics"]["savings"], x["deal_score"], x["store_id"], x["product_id"]), reverse=True)
    elif sort == "price":
        valid_res.sort(key=lambda x: (x["current_price"], -x["deal_score"], x["store_id"], x["product_id"]))
    elif sort == "recent":
        valid_res.sort(key=lambda x: (x.get("timestamp", ""), x["deal_score"], x["store_id"], x["product_id"]), reverse=True)
    else:
        valid_res.sort(key=lambda x: (x["confidence_rank"], x["deal_score"], x.get("timestamp", ""), x["store_id"], x["product_id"]), reverse=True)
        
    total = len(valid_res)
    start = (page - 1) * per_page
    end = start + per_page
    
    items = valid_res[start:end]
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }
