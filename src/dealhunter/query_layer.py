import sqlite3

from dealhunter.eligibility import EligibilityEngine

def _build_where(filters: dict, config: dict = None, exclude_dim=None):
    config = config or {}
    where_clauses = []
    params = []
    
    # 0. Eligibility (Provider + Membership visibility)
    engine = EligibilityEngine(config)
    vis_sql, vis_params = engine.get_sql_visibility_condition(provider_col="p.provider", has_pro_col="o.has_pro_offer")
    if vis_sql:
        where_clauses.append(vis_sql)
        params.extend(vis_params)
        
    # 0b. Provider Explicit Filter
    providers = filters.get("providers")
    if providers and exclude_dim != "providers":
        placeholders = ",".join(["?"] * len(providers))
        where_clauses.append(f"p.provider IN ({placeholders})")
        params.extend(providers)
        
    # 1. Verticals
    verticals = filters.get("verticals")
    if verticals and exclude_dim != "verticals":
        placeholders = ",".join(["?"] * len(verticals))
        where_clauses.append(f"(LOWER(s.vertical) IN ({placeholders}) OR (s.vertical IS NULL AND LOWER(s.type) IN ({placeholders})))")
        params.extend([v.lower() for v in verticals] * 2)
        
    # 2. Stores
    store_ids = filters.get("store_ids") or []
    store_identities = filters.get("store_identities") or []
    if (store_ids or store_identities) and exclude_dim != "store_ids":
        store_clauses = []
        if store_ids:
            placeholders = ",".join(["?"] * len(store_ids))
            store_clauses.append(f"p.store_id IN ({placeholders})")
            params.extend(store_ids)
        for provider, store_id in store_identities:
            store_clauses.append("(p.provider = ? AND p.store_id = ?)")
            params.extend([provider, store_id])
        where_clauses.append("(" + " OR ".join(store_clauses) + ")")
        
    # 3. Store Facets
    store_facets = filters.get("store_facets")
    if store_facets and exclude_dim != "store_facets":
        placeholders = ",".join(["?"] * len(store_facets))
        where_clauses.append(f"EXISTS (SELECT 1 FROM store_facets sf WHERE sf.provider = p.provider AND sf.store_id = p.store_id AND sf.raw_value IN ({placeholders}))")
        params.extend(store_facets)
        
    # 4. Categories (with priority fallback)
    categories = filters.get("categories")
    if categories and exclude_dim != "categories":
        placeholders = ",".join(["?"] * len(categories))
        clause = f"""(
            EXISTS (
                SELECT 1 FROM product_memberships pm 
                WHERE pm.provider = p.provider AND pm.store_id = p.store_id AND pm.product_id = p.product_id AND pm.semantic_type = 'CATEGORY' AND pm.raw_name IN ({placeholders})
            )
            OR (
                NOT EXISTS (
                    SELECT 1 FROM product_memberships pm 
                    WHERE pm.provider = p.provider AND pm.store_id = p.store_id AND pm.product_id = p.product_id AND pm.semantic_type = 'CATEGORY'
                )
                AND p.category IN ({placeholders})
            )
        )"""
        where_clauses.append(clause)
        params.extend(categories * 2)
        
    # 5. Collections
    collections = filters.get("collections")
    if collections and exclude_dim != "collections":
        placeholders = ",".join(["?"] * len(collections))
        where_clauses.append(f"EXISTS (SELECT 1 FROM product_memberships pm WHERE pm.provider = p.provider AND pm.store_id = p.store_id AND pm.product_id = p.product_id AND pm.semantic_type = 'COLLECTION' AND pm.raw_name IN ({placeholders}))")
        params.extend(collections)
        
    # 6. Availability
    availability = filters.get("availability")
    if availability and exclude_dim != "availability":
        where_clauses.append("o.availability = ?")
        params.append(availability)
        
    # 7. Commercial Channel
    if exclude_dim != "commercial":
        channel = filters.get("channel", "PUBLIC")
        min_discount = filters.get("min_discount")
        max_price = filters.get("max_price")
        
        if channel == "PUBLIC":
            if min_discount is not None:
                where_clauses.append("o.discount_effective >= ? AND o.price > 0")
                params.append(min_discount)
            if max_price is not None:
                where_clauses.append("o.price <= ? AND o.price > 0")
                params.append(max_price)
                
        elif channel == "PRO":
            where_clauses.append("o.has_pro_offer = 1")
            if min_discount is not None:
                where_clauses.append("o.pro_discount_effective >= ? AND o.pro_price > 0")
                params.append(min_discount)
            if max_price is not None:
                where_clauses.append("o.pro_price <= ? AND o.pro_price > 0")
                params.append(max_price)
                
        elif channel == "ALL":
            if min_discount is not None and max_price is not None:
                where_clauses.append("((o.discount_effective >= ? AND o.price <= ? AND o.price > 0) OR (o.has_pro_offer = 1 AND o.pro_discount_effective >= ? AND o.pro_price <= ? AND o.pro_price > 0))")
                params.extend([min_discount, max_price, min_discount, max_price])
            elif min_discount is not None:
                where_clauses.append("((o.discount_effective >= ? AND o.price > 0) OR (o.has_pro_offer = 1 AND o.pro_discount_effective >= ? AND o.pro_price > 0))")
                params.extend([min_discount, min_discount])
            elif max_price is not None:
                where_clauses.append("((o.price <= ? AND o.price > 0) OR (o.has_pro_offer = 1 AND o.pro_price <= ? AND o.pro_price > 0))")
                params.extend([max_price, max_price])
                
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    return where_sql, params

def _base_query():
    return '''
        SELECT p.product_id, p.store_id, p.name, s.name as store_name, s.type as store_type, s.vertical as store_vertical, p.brand, p.category as legacy_category,
               CASE WHEN o.price > 0 THEN o.price ELSE NULL END as current_price,
               CASE WHEN o.price > 0 THEN o.original_price ELSE NULL END as original_price,
               CASE WHEN o.price > 0 THEN o.discount_effective ELSE 0 END as discount_effective,
               o.promotion_type, o.promotion_label,
               o.has_pro_offer,
               CASE WHEN o.pro_price > 0 THEN o.pro_price ELSE NULL END as pro_price,
               CASE WHEN o.pro_price > 0 THEN o.pro_discount_effective ELSE 0 END as pro_discount_effective,
               o.limit_info, o.availability, o.timestamp as ts,
               p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.provider
        FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        JOIN (
            SELECT provider, product_id, store_id, price, original_price, discount_effective, promotion_type, promotion_label,
                   has_pro_offer, pro_price, pro_discount_effective, limit_info, availability, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY provider, store_id, product_id ORDER BY timestamp DESC, id DESC) as rn
            FROM trusted_observations
        ) o ON p.provider = o.provider AND p.product_id = o.product_id AND p.store_id = o.store_id AND o.rn = 1
    '''

def build_faceted_query(filters: dict, config: dict = None):
    config = config or {}
    base_query = _base_query()
    where_sql, params = _build_where(filters, config)
    
    # Sorting
    sort = filters.get("sort", "discount")
    desc = filters.get("desc", True)
    dir_sql = "DESC" if desc else "ASC"
    
    channel = filters.get("channel", "PUBLIC")
    
    # If policy is show_but_exclude, we need to sort those offers to the bottom.
    engine = EligibilityEngine(config)
    policy = engine.comparison_policy
    
    # We construct a CASE statement to determine ranking eligibility at DB level for sorting
    # A product is ineligible if it requires a membership, the membership is not active, and policy is show_but_exclude
    ranking_eligible_expr = "1"
    if policy == "show_but_exclude":
        # Rappi Pro check
        if engine.get_membership_status("rappi_pro") != "active":
            ranking_eligible_expr = f"CASE WHEN p.provider = 'rappi' AND o.has_pro_offer = 1 THEN 0 ELSE {ranking_eligible_expr} END"
        # Uber One check
        if engine.get_membership_status("uber_one") != "active":
            ranking_eligible_expr = f"CASE WHEN p.provider = 'uber_eats' AND o.has_pro_offer = 1 THEN 0 ELSE {ranking_eligible_expr} END"
            
    # Sort uneligible to the bottom always
    order_sql = f"ORDER BY {ranking_eligible_expr} DESC, "
    
    # Guard against invalid prices dominating sorts
    if channel == "PRO":
        order_sql += "CASE WHEN o.pro_price > 0 THEN 1 ELSE 0 END DESC, "
    else:
        order_sql += "CASE WHEN o.price > 0 THEN 1 ELSE 0 END DESC, "

    if sort == "discount":
        if channel == "PRO":
            order_sql += f"o.pro_discount_effective {dir_sql}, o.pro_price ASC"
        else:
            order_sql += f"o.discount_effective {dir_sql}, o.price ASC"
    elif sort == "price":
        if channel == "PRO":
            order_sql += f"o.pro_price {dir_sql}, o.pro_discount_effective DESC"
        else:
            order_sql += f"o.price {dir_sql}, o.discount_effective DESC"
    elif sort == "name":
        order_sql += f"p.name {dir_sql}"
    else:
        order_sql += f"p.product_id {dir_sql}"
        
    order_sql += ", p.product_id ASC"
        
    limit = filters.get("limit", 25)
    offset = filters.get("offset", 0)
    
    query = f"""
        {base_query}
        {where_sql}
        {order_sql}
        LIMIT {int(limit)} OFFSET {int(offset)}
    """
    
    count_query = f"""
        SELECT COUNT(*) FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        JOIN (
            SELECT provider, product_id, store_id, price, original_price, discount_effective, promotion_type, promotion_label,
                   has_pro_offer, pro_price, pro_discount_effective, limit_info, availability, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY provider, store_id, product_id ORDER BY timestamp DESC, id DESC) as rn
            FROM trusted_observations
        ) o ON p.provider = o.provider AND p.product_id = o.product_id AND p.store_id = o.store_id AND o.rn = 1
        {where_sql}
    """
    
    return query, count_query, params

def get_facet_counts(conn, filters: dict, config: dict = None):
    config = config or {}
    
    def get_base_join(w_sql):
        if "o." in w_sql:
            return '''
                FROM products p
                JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
                JOIN (
                    SELECT provider, product_id, store_id, price, original_price, discount_effective, promotion_type, promotion_label,
                           has_pro_offer, pro_price, pro_discount_effective, limit_info, availability, timestamp,
                           ROW_NUMBER() OVER (PARTITION BY provider, store_id, product_id ORDER BY timestamp DESC, id DESC) as rn
                    FROM trusted_observations
                ) o ON p.provider = o.provider AND p.product_id = o.product_id AND p.store_id = o.store_id AND o.rn = 1
            '''
        else:
            return '''
                FROM products p
                JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
            '''
    
    counts = {}

    
    # Categories (excluding category filter so we see all available for current scope)
    where_sql, params = _build_where(filters, config, exclude_dim="categories")
    c = conn.cursor()
    # To get available categories, we union trusted categories + fallback categories for the MATCHING products
    cat_query = f"""
        SELECT DISTINCT cat_name FROM (
            SELECT pm.raw_name as cat_name
            {get_base_join(where_sql)}
            JOIN product_memberships pm ON p.provider = pm.provider AND p.store_id = pm.store_id AND p.product_id = pm.product_id
            {where_sql} {'AND' if where_sql else 'WHERE'} pm.semantic_type = 'CATEGORY'
            
            UNION ALL
            
            SELECT p.category as cat_name
            {get_base_join(where_sql)}
            {where_sql} {'AND' if where_sql else 'WHERE'} p.category IS NOT NULL AND p.category != ''
            AND NOT EXISTS (
                SELECT 1 FROM product_memberships pm2 
                WHERE pm2.provider = p.provider AND pm2.store_id = p.store_id AND pm2.product_id = p.product_id AND pm2.semantic_type = 'CATEGORY'
            )
        )
        ORDER BY cat_name
    """
    c.execute(cat_query, params * 2) 
    counts["categories"] = [r[0] for r in c.fetchall()]
    
    # Collections
    where_sql, params = _build_where(filters, config, exclude_dim="collections")
    col_query = f"""
        SELECT DISTINCT pm.raw_name
        {get_base_join(where_sql)}
        JOIN product_memberships pm ON p.provider = pm.provider AND p.store_id = pm.store_id AND p.product_id = pm.product_id
        {where_sql} {'AND' if where_sql else 'WHERE'} pm.semantic_type = 'COLLECTION'
        ORDER BY pm.raw_name
    """
    c.execute(col_query, params)
    counts["collections"] = [r[0] for r in c.fetchall()]
    
    # Verticals
    where_sql, params = _build_where(filters, config, exclude_dim="verticals")
    vert_query = f"""
        SELECT DISTINCT COALESCE(s.vertical, s.type)
        {get_base_join(where_sql)}
        {where_sql}
    """
    c.execute(vert_query, params)
    counts["verticals"] = [r[0] for r in c.fetchall()]
    
    # Store Facets
    where_sql, params = _build_where(filters, config, exclude_dim="store_facets")
    sf_query = f"""
        SELECT DISTINCT sf.raw_value
        {get_base_join(where_sql)}
        JOIN store_facets sf ON p.provider = sf.provider AND p.store_id = sf.store_id
        {where_sql}
    """
    c.execute(sf_query, params)
    counts["store_facets"] = [r[0] for r in c.fetchall()]
    

    # Stores
    where_sql, params = _build_where(filters, config, exclude_dim="store_ids")
    store_query = f'''
        SELECT DISTINCT p.provider, p.store_id, s.name
        {get_base_join(where_sql)}
        {where_sql}
        ORDER BY s.name
    '''
    c.execute(store_query, params)
    counts["stores"] = [
        {
            "provider": r[0],
            "store_id": r[1],
            "filter_key": f"{r[0]}::{r[1]}",
            "name": r[2],
        }
        for r in c.fetchall()
    ]
    
    return counts
