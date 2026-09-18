import sqlite3

from dealhunter.eligibility import EligibilityEngine
from dealhunter.commerce import raw_types_for_commerce, raw_types_for_domain

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

        # Expand 'restaurants' to also check for 'restaurant'
        expanded_verticals = []
        for v in verticals:
            v = v.lower()
            expanded_verticals.append(v)
            if v == 'restaurants':
                expanded_verticals.append('restaurant')
            elif v == 'restaurant':
                expanded_verticals.append('restaurants')

        placeholders = ",".join(["?"] * len(expanded_verticals))
        where_clauses.append(f"(LOWER(s.vertical) IN ({placeholders}) OR (s.vertical IS NULL AND LOWER(s.type) IN ({placeholders})))")
        params.extend(expanded_verticals * 2)

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

    # 2b. Commercial identity and catalog domain. Values are explicit IDs/enums;
    # OR within each dimension and AND across dimensions.
    merchant_ids = filters.get("merchant_ids") or []
    if merchant_ids and exclude_dim != "merchant_ids":
        placeholders = ",".join("?" for _ in merchant_ids)
        where_clauses.append(f"s.merchant_id IN ({placeholders})")
        params.extend(merchant_ids)

    location_ids = filters.get("location_ids") or []
    if location_ids and exclude_dim != "location_ids":
        placeholders = ",".join("?" for _ in location_ids)
        where_clauses.append(f"s.location_id IN ({placeholders})")
        params.extend(location_ids)

    excluded_locations = filters.get("exclude_location_ids") or []
    if excluded_locations and exclude_dim != "exclude_location_ids":
        placeholders = ",".join("?" for _ in excluded_locations)
        where_clauses.append(f"(s.location_id IS NULL OR s.location_id NOT IN ({placeholders}))")
        params.extend(excluded_locations)

    commerce_types = filters.get("commerce_types") or []
    if commerce_types and exclude_dim != "commerce_types":
        placeholders = ",".join("?" for _ in commerce_types)
        raw_types = raw_types_for_commerce(commerce_types)
        if raw_types:
            raw_placeholders = ",".join("?" for _ in raw_types)
            where_clauses.append(
                f"(s.commerce_type IN ({placeholders}) OR "
                f"(s.commerce_type = 'UNKNOWN' AND LOWER(TRIM(COALESCE(s.type, ''))) IN ({raw_placeholders})))"
            )
            params.extend(commerce_types)
            params.extend(raw_types)
        else:
            where_clauses.append(f"s.commerce_type IN ({placeholders})")
            params.extend(commerce_types)

    catalog_domains = filters.get("catalog_domains") or []
    if catalog_domains and exclude_dim != "catalog_domains":
        placeholders = ",".join("?" for _ in catalog_domains)
        raw_types = raw_types_for_domain(catalog_domains)
        if raw_types:
            raw_placeholders = ",".join("?" for _ in raw_types)
            where_clauses.append(
                f"(s.catalog_domain IN ({placeholders}) OR "
                f"(s.catalog_domain = 'UNKNOWN' AND LOWER(TRIM(COALESCE(s.type, ''))) IN ({raw_placeholders})))"
            )
            params.extend(catalog_domains)
            params.extend(raw_types)
        else:
            where_clauses.append(f"s.catalog_domain IN ({placeholders})")
            params.extend(catalog_domains)

    brands = filters.get("brands") or []
    if brands and exclude_dim != "brands":
        placeholders = ",".join("?" for _ in brands)
        where_clauses.append(f"p.brand IN ({placeholders})")
        params.extend(brands)

    # 2c. DealHunter browse taxonomy. Raw provider evidence remains in
    # product_memberships and maps to reviewed browse nodes separately.
    browse_node_ids = filters.get("browse_node_ids") or []
    if browse_node_ids and exclude_dim != "browse_node_ids":
        want_unclassified = "UNCLASSIFIED" in browse_node_ids
        selected = [node for node in browse_node_ids if node != "UNCLASSIFIED"]
        browse_clauses = []
        if selected:
            placeholders = ",".join("?" for _ in selected)
            browse_clauses.append(f"""EXISTS (
                SELECT 1
                FROM product_memberships pm
                JOIN browse_mappings bm
                  ON bm.provider = pm.provider
                 AND bm.raw_type = COALESCE(pm.raw_type, '')
                 AND bm.raw_name = pm.raw_name
                 AND bm.raw_path = COALESCE(pm.path, '')
                WHERE pm.provider = p.provider
                  AND pm.store_id = p.store_id
                  AND pm.product_id = p.product_id
                  AND bm.browse_node_id IN (
                    WITH RECURSIVE descendants(browse_node_id) AS (
                        SELECT browse_node_id FROM browse_nodes
                        WHERE active = 1 AND browse_node_id IN ({placeholders})
                        UNION ALL
                        SELECT child.browse_node_id
                        FROM browse_nodes child
                        JOIN descendants parent ON child.parent_id = parent.browse_node_id
                        WHERE child.active = 1
                    )
                    SELECT browse_node_id FROM descendants
                  )
            )""")
            params.extend(selected)
        if want_unclassified:
            browse_clauses.append("""NOT EXISTS (
                SELECT 1
                FROM product_memberships pm
                JOIN browse_mappings bm
                  ON bm.provider = pm.provider
                 AND bm.raw_type = COALESCE(pm.raw_type, '')
                 AND bm.raw_name = pm.raw_name
                 AND bm.raw_path = COALESCE(pm.path, '')
                WHERE pm.provider = p.provider
                  AND pm.store_id = p.store_id
                  AND pm.product_id = p.product_id
            )""")
        where_clauses.append("(" + " OR ".join(browse_clauses) + ")")

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

def _latest_observation_join():
    return '''
        JOIN trusted_observations o
          ON p.provider = o.provider
         AND p.product_id = o.product_id
         AND p.store_id = o.store_id
         AND o.id = (
            SELECT o2.id
            FROM trusted_observations o2
            WHERE o2.provider = p.provider
              AND o2.product_id = p.product_id
              AND o2.store_id = p.store_id
            ORDER BY o2.timestamp DESC, o2.id DESC
            LIMIT 1
         )
    '''


def _base_query(extra_select=""):
    extra_sql = f", {extra_select}" if extra_select else ""
    return f'''
        SELECT p.product_id, p.store_id, p.name, s.name as store_name, s.type as store_type, s.vertical as store_vertical, p.brand, p.category as legacy_category,
               CASE WHEN o.price > 0 THEN o.price ELSE NULL END as current_price,
               CASE WHEN o.price > 0 THEN o.original_price ELSE NULL END as original_price,
               CASE WHEN o.price > 0 THEN o.discount_effective ELSE 0 END as discount_effective,
               o.promotion_type, o.promotion_label,
               o.has_pro_offer,
               CASE WHEN o.pro_price > 0 THEN o.pro_price ELSE NULL END as pro_price,
               CASE WHEN o.pro_price > 0 THEN o.pro_discount_effective ELSE 0 END as pro_discount_effective,
               o.limit_info, o.availability, o.timestamp as ts,
               p.quantity, p.unit, p.normalized_quantity, p.normalized_unit, p.provider{extra_sql}
        FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        {_latest_observation_join()}
    '''

def _ordering_spec(filters: dict, config: dict):
    """Return deterministic ORDER BY components shared by offset/keyset queries."""
    sort = filters.get("sort", "discount")
    desc = filters.get("desc", True)
    direction = "DESC" if desc else "ASC"
    channel = filters.get("channel", "PUBLIC")

    engine = EligibilityEngine(config)
    # Avoid SQLite positional ORDER BY 1 syntax when ranking is constant.
    ranking_expr = "CAST(1 AS INTEGER)"
    if engine.comparison_policy == "show_but_exclude":
        if engine.get_membership_status("rappi_pro") != "active":
            ranking_expr = f"CASE WHEN p.provider = 'rappi' AND o.has_pro_offer = 1 THEN 0 ELSE {ranking_expr} END"
        if engine.get_membership_status("uber_one") != "active":
            ranking_expr = f"CASE WHEN p.provider = 'uber_eats' AND o.has_pro_offer = 1 THEN 0 ELSE {ranking_expr} END"

    price_expr = "o.pro_price" if channel == "PRO" else "o.price"
    discount_expr = "o.pro_discount_effective" if channel == "PRO" else "o.discount_effective"
    valid_expr = f"CASE WHEN {price_expr} > 0 THEN 1 ELSE 0 END"

    if sort == "discount":
        primary_expr = f"COALESCE({discount_expr}, 0)"
        secondary_expr = f"COALESCE({price_expr}, 0)"
        primary_dir, secondary_dir = direction, "ASC"
    elif sort == "price":
        primary_expr = f"COALESCE({price_expr}, 0)"
        secondary_expr = f"COALESCE({discount_expr}, 0)"
        primary_dir, secondary_dir = direction, "DESC"
    elif sort == "name":
        primary_expr = "COALESCE(p.name, '')"
        secondary_expr = "''"
        primary_dir, secondary_dir = direction, "ASC"
    elif sort == "savings":
        primary_expr = (
            f"CASE WHEN {price_expr} > 0 AND o.original_price > {price_expr} "
            f"THEN o.original_price - {price_expr} ELSE 0 END"
        )
        secondary_expr = f"COALESCE({price_expr}, 0)"
        primary_dir, secondary_dir = direction, "ASC"
    elif sort == "recent":
        primary_expr = "COALESCE(o.timestamp, '')"
        secondary_expr = "o.id"
        primary_dir, secondary_dir = direction, direction
    elif sort == "score":
        # Legacy internal callers used ``score`` only as a stable catalog order.
        # It is not exposed as a catalog scoring claim; keep deterministic
        # compatibility while real Deal Score ranking remains in web.best.
        primary_expr = "COALESCE(p.product_id, '')"
        secondary_expr = "''"
        primary_dir, secondary_dir = direction, "ASC"
    else:
        raise ValueError(f"unsupported catalog sort: {sort}")

    return [
        (ranking_expr, "DESC", "__rank"),
        (valid_expr, "DESC", "__valid"),
        (primary_expr, primary_dir, "__primary"),
        (secondary_expr, secondary_dir, "__secondary"),
        ("p.provider", "ASC", "provider"),
        ("p.store_id", "ASC", "store_id"),
        ("p.product_id", "ASC", "product_id"),
    ]


def _order_sql(ordering, *, aliases=False):
    parts = []
    for expr, direction, alias in ordering:
        parts.append(f"{alias if aliases else expr} {direction}")
    return "ORDER BY " + ", ".join(parts)


def _cursor_predicate(ordering, cursor_values):
    """Build a mixed-direction lexicographic 'strictly after cursor' predicate."""
    if cursor_values is None:
        return "", []
    if len(cursor_values) != len(ordering):
        raise ValueError("cursor shape does not match ordering")

    clauses = []
    params = []
    for idx, (_, direction, alias) in enumerate(ordering):
        prefix = []
        for prev in range(idx):
            prefix.append(f"{ordering[prev][2]} = ?")
            params.append(cursor_values[prev])
        op = "<" if direction == "DESC" else ">"
        prefix.append(f"{alias} {op} ?")
        params.append(cursor_values[idx])
        clauses.append("(" + " AND ".join(prefix) + ")")
    return "WHERE " + " OR ".join(clauses), params


def build_faceted_query(filters: dict, config: dict = None):
    """Legacy-compatible offset query with a fully deterministic ordering."""
    config = config or {}
    base_query = _base_query()
    where_sql, params = _build_where(filters, config)
    ordering = _ordering_spec(filters, config)
    order_sql = _order_sql(ordering)

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
        {_latest_observation_join()}
        {where_sql}
    """
    return query, count_query, params


def build_faceted_cursor_query(filters: dict, cursor_values=None, config: dict = None):
    """Keyset query for large catalogs while preserving the existing filter contract.

    Returns query/count SQL plus separate parameter lists because cursor parameters
    apply only to the page query, never to the total count.
    """
    config = config or {}
    base_query = _base_query()
    where_sql, base_params = _build_where(filters, config)
    ordering = _ordering_spec(filters, config)
    cursor_sql, cursor_params = _cursor_predicate(ordering, cursor_values)

    # The first four ordering expressions are appended as hidden page keys. The
    # final identity keys already exist in the base select (provider/store/product).
    hidden = ", ".join(f"{expr} AS {alias}" for expr, _, alias in ordering[:4])
    limit = int(filters.get("limit", 25))
    query = f"""
        WITH catalog_rows AS (
            {_base_query(hidden)}
            {where_sql}
        )
        SELECT * FROM catalog_rows
        {cursor_sql}
        {_order_sql(ordering, aliases=True)}
        LIMIT {limit}
    """
    count_query = f"""
        SELECT COUNT(*) FROM products p
        JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
        {_latest_observation_join()}
        {where_sql}
    """
    return query, count_query, list(base_params) + cursor_params, list(base_params)

def get_facet_counts(conn, filters: dict, config: dict = None):
    config = config or {}

    def get_base_join(w_sql):
        if "o." in w_sql:
            return f'''
                FROM products p
                JOIN stores s ON p.provider = s.provider AND p.store_id = s.store_id
                {_latest_observation_join()}
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


    # Commercial identity facets
    where_sql, params = _build_where(filters, config, exclude_dim="merchant_ids")
    merchant_query = f"""
        SELECT DISTINCT m.merchant_id, m.name
        {get_base_join(where_sql)}
        JOIN merchants m ON s.merchant_id = m.merchant_id
        {where_sql}
        ORDER BY m.name, m.merchant_id
    """
    c.execute(merchant_query, params)
    counts["merchants"] = [{"id": r[0], "name": r[1]} for r in c.fetchall()]

    where_sql, params = _build_where(filters, config, exclude_dim="location_ids")
    location_query = f"""
        SELECT DISTINCT ml.location_id, ml.merchant_id, ml.name
        {get_base_join(where_sql)}
        JOIN merchant_locations ml ON s.location_id = ml.location_id
        {where_sql}
        ORDER BY ml.name, ml.location_id
    """
    c.execute(location_query, params)
    counts["locations"] = [
        {"id": r[0], "merchant_id": r[1], "name": r[2]} for r in c.fetchall()
    ]

    where_sql, params = _build_where(filters, config, exclude_dim="commerce_types")
    commerce_query = f"""
        SELECT DISTINCT s.commerce_type
        {get_base_join(where_sql)}
        {where_sql} {'AND' if where_sql else 'WHERE'} s.commerce_type IS NOT NULL AND s.commerce_type != 'UNKNOWN'
        ORDER BY s.commerce_type
    """
    c.execute(commerce_query, params)
    counts["commerce_types"] = [r[0] for r in c.fetchall()]

    where_sql, params = _build_where(filters, config, exclude_dim="catalog_domains")
    domain_query = f"""
        SELECT DISTINCT s.catalog_domain
        {get_base_join(where_sql)}
        {where_sql} {'AND' if where_sql else 'WHERE'} s.catalog_domain IS NOT NULL AND s.catalog_domain != 'UNKNOWN'
        ORDER BY s.catalog_domain
    """
    c.execute(domain_query, params)
    counts["catalog_domains"] = [r[0] for r in c.fetchall()]

    where_sql, params = _build_where(filters, config, exclude_dim="brands")
    brand_query = f"""
        SELECT DISTINCT p.brand
        {get_base_join(where_sql)}
        {where_sql} {'AND' if where_sql else 'WHERE'} p.brand IS NOT NULL AND TRIM(p.brand) != ''
        ORDER BY p.brand
    """
    c.execute(brand_query, params)
    counts["brands"] = [r[0] for r in c.fetchall()]

    # Reviewed DealHunter browse taxonomy; raw provider memberships remain the evidence source.
    where_sql, params = _build_where(filters, config, exclude_dim="browse_node_ids")
    browse_query = f"""
        SELECT DISTINCT bn.browse_node_id, bn.parent_id, bn.level, bn.name
        {get_base_join(where_sql)}
        JOIN product_memberships pm
          ON p.provider = pm.provider
         AND p.store_id = pm.store_id
         AND p.product_id = pm.product_id
        JOIN browse_mappings bm
          ON bm.provider = pm.provider
         AND bm.raw_type = COALESCE(pm.raw_type, '')
         AND bm.raw_name = pm.raw_name
         AND bm.raw_path = COALESCE(pm.path, '')
        JOIN browse_nodes bn ON bn.browse_node_id = bm.browse_node_id
        {where_sql} {'AND' if where_sql else 'WHERE'} bn.active = 1
        ORDER BY bn.sort_order, bn.name, bn.browse_node_id
    """
    c.execute(browse_query, params)
    counts["browse_nodes"] = [
        {"id": r[0], "parent_id": r[1], "level": r[2], "name": r[3]}
        for r in c.fetchall()
    ]

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
