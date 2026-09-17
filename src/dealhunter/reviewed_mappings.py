"""Explicit reviewed mappings for commercial identity and browse taxonomy.

These helpers never infer authority from display names. Raw provider identity remains
(provider, store_id); unmapped records remain UNRESOLVED / UNCLASSIFIED.
"""

from dealhunter.providers.registry import validate_provider

BROWSE_LEVELS = {"DEPARTMENT", "SECTION", "CATEGORY", "SUBCATEGORY"}


def _required(value, name):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def list_unresolved_listings(conn, provider=None):
    params = []
    where = "WHERE (merchant_id IS NULL OR location_id IS NULL)"
    if provider:
        provider = validate_provider(provider)
        where += " AND provider = ?"
        params.append(provider)
    rows = conn.execute(
        f"""SELECT provider, store_id, name, merchant_id, location_id
            FROM stores {where}
            ORDER BY provider, name, store_id""",
        params,
    ).fetchall()
    return [
        {
            "provider": row[0], "store_id": row[1], "name": row[2],
            "merchant_id": row[3], "location_id": row[4], "status": "UNRESOLVED",
        }
        for row in rows
    ]


def confirm_merchant_location(
    conn, *, provider, store_id, merchant_id, merchant_name,
    location_id, location_name, source="reviewed",
):
    """Persist one explicitly reviewed Provider Listing -> Merchant -> Location mapping."""
    provider = validate_provider(provider)
    store_id = _required(store_id, "store_id")
    merchant_id = _required(merchant_id, "merchant_id")
    merchant_name = _required(merchant_name, "merchant_name")
    location_id = _required(location_id, "location_id")
    location_name = _required(location_name, "location_name")
    source = _required(source, "source")

    with conn:
        store = conn.execute(
            "SELECT merchant_id, location_id FROM stores WHERE provider=? AND store_id=?",
            (provider, store_id),
        ).fetchone()
        if not store:
            raise ValueError(f"unknown provider listing: ({provider}, {store_id})")
        if (store[0] and store[0] != merchant_id) or (store[1] and store[1] != location_id):
            raise ValueError("provider listing is already mapped; clear it before remapping")

        merchant = conn.execute(
            "SELECT name FROM merchants WHERE merchant_id=?", (merchant_id,)
        ).fetchone()
        if merchant and merchant[0] != merchant_name:
            raise ValueError("merchant_id already exists with different reviewed name")
        if not merchant:
            conn.execute(
                "INSERT INTO merchants (merchant_id,name,source) VALUES (?,?,?)",
                (merchant_id, merchant_name, source),
            )

        location = conn.execute(
            "SELECT merchant_id,name FROM merchant_locations WHERE location_id=?",
            (location_id,),
        ).fetchone()
        if location and (location[0] != merchant_id or location[1] != location_name):
            raise ValueError("location_id already exists with different reviewed identity")
        if not location:
            conn.execute(
                "INSERT INTO merchant_locations (location_id,merchant_id,name,source) VALUES (?,?,?,?)",
                (location_id, merchant_id, location_name, source),
            )

        conn.execute(
            "UPDATE stores SET merchant_id=?, location_id=? WHERE provider=? AND store_id=?",
            (merchant_id, location_id, provider, store_id),
        )


def clear_merchant_location_mapping(conn, *, provider, store_id):
    provider = validate_provider(provider)
    store_id = _required(store_id, "store_id")
    with conn:
        cur = conn.execute(
            "UPDATE stores SET merchant_id=NULL, location_id=NULL WHERE provider=? AND store_id=?",
            (provider, store_id),
        )
        if cur.rowcount != 1:
            raise ValueError(f"unknown provider listing: ({provider}, {store_id})")


def list_unclassified_memberships(conn, provider=None):
    params = []
    provider_sql = ""
    if provider:
        provider = validate_provider(provider)
        provider_sql = "AND pm.provider = ?"
        params.append(provider)
    rows = conn.execute(
        f"""
        SELECT DISTINCT pm.provider, pm.raw_type, pm.raw_name, COALESCE(pm.path,''), pm.source
        FROM product_memberships pm
        WHERE NOT EXISTS (
            SELECT 1 FROM browse_mappings bm
            WHERE bm.provider = pm.provider
              AND bm.raw_type = pm.raw_type
              AND bm.raw_name = pm.raw_name
              AND bm.raw_path = COALESCE(pm.path,'')
        )
        {provider_sql}
        ORDER BY pm.provider, pm.raw_type, pm.raw_name, COALESCE(pm.path,'')
        """,
        params,
    ).fetchall()
    return [
        {
            "provider": row[0], "raw_type": row[1], "raw_name": row[2],
            "raw_path": row[3], "source": row[4], "status": "UNCLASSIFIED",
        }
        for row in rows
    ]


def add_browse_node(conn, browse_node_id, *, name, level, parent_id=None):
    browse_node_id = _required(browse_node_id, "browse_node_id")
    name = _required(name, "name")
    level = _required(level, "level").upper()
    if level not in BROWSE_LEVELS:
        raise ValueError(f"unsupported browse level: {level}")
    parent_id = str(parent_id).strip() if parent_id else None

    with conn:
        if parent_id and not conn.execute(
            "SELECT 1 FROM browse_nodes WHERE browse_node_id=?", (parent_id,)
        ).fetchone():
            raise ValueError(f"unknown parent browse node: {parent_id}")
        existing = conn.execute(
            "SELECT parent_id,level,name FROM browse_nodes WHERE browse_node_id=?",
            (browse_node_id,),
        ).fetchone()
        expected = (parent_id, level, name)
        if existing and tuple(existing) != expected:
            raise ValueError("browse_node_id already exists with different reviewed definition")
        if not existing:
            conn.execute(
                "INSERT INTO browse_nodes (browse_node_id,parent_id,level,name) VALUES (?,?,?,?)",
                (browse_node_id, parent_id, level, name),
            )


def confirm_browse_mapping(
    conn, *, provider, raw_type, raw_name, raw_path, browse_node_id, source="reviewed",
):
    provider = validate_provider(provider)
    raw_type = _required(raw_type, "raw_type")
    raw_name = _required(raw_name, "raw_name")
    raw_path = "" if raw_path is None else str(raw_path)
    browse_node_id = _required(browse_node_id, "browse_node_id")
    source = _required(source, "source")

    with conn:
        if not conn.execute(
            "SELECT 1 FROM browse_nodes WHERE browse_node_id=? AND active=1",
            (browse_node_id,),
        ).fetchone():
            raise ValueError(f"unknown or inactive browse node: {browse_node_id}")
        existing = conn.execute(
            """SELECT browse_node_id FROM browse_mappings
               WHERE provider=? AND raw_type=? AND raw_name=? AND raw_path=?""",
            (provider, raw_type, raw_name, raw_path),
        ).fetchall()
        if existing and any(row[0] != browse_node_id for row in existing):
            raise ValueError("raw taxonomy evidence already maps to a different browse node")
        conn.execute(
            """INSERT OR IGNORE INTO browse_mappings
               (provider,raw_type,raw_name,raw_path,browse_node_id,source)
               VALUES (?,?,?,?,?,?)""",
            (provider, raw_type, raw_name, raw_path, browse_node_id, source),
        )


def clear_browse_mapping(conn, *, provider, raw_type, raw_name, raw_path, browse_node_id):
    provider = validate_provider(provider)
    with conn:
        cur = conn.execute(
            """DELETE FROM browse_mappings
               WHERE provider=? AND raw_type=? AND raw_name=? AND raw_path=? AND browse_node_id=?""",
            (provider, raw_type, raw_name, "" if raw_path is None else str(raw_path), browse_node_id),
        )
        if cur.rowcount != 1:
            raise ValueError("reviewed browse mapping not found")
