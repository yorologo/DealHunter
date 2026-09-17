from flask import render_template, request, current_app, redirect, url_for, flash, jsonify, abort
from dealhunter.config import get_merged_config
from dealhunter.providers.registry import KNOWN_PROVIDERS
from dealhunter.web.params import QueryParamError, parse_cursor, parse_enum, parse_float, parse_page
from dealhunter.web.security import local_redirect_target
from dealhunter.web.queries import (
    get_home_metrics, get_home_deals, get_watchlist, search_local, 
    get_product_detail, get_product_compare, get_anchor_compare,
    get_deals, get_catalog, get_categories, get_browse_categories, get_browse_node, get_merchants_directory, get_stores, get_store_detail, get_available_stores, get_available_categories, get_ui_facets
)

CATALOG_SORTS = {"discount", "savings", "price_asc", "price_desc", "name_asc", "recent"}
BEST_SORTS = {"score", "discount", "savings", "price", "recent"}
DEAL_SORTS = {"opportunity", "discount", "drop", "price", "recent", "name"}
DEAL_TABS = {"Todo", "NEW_LOW", "REAL_DEAL", "GOOD_PRICE", "PRICE_DROP", "TARGET_PRICE", "BACK_IN_STOCK", "SUSPICIOUS_REFERENCE_PRICE"}
CHANNELS = {"PUBLIC", "PRO", "ALL"}
BRANCH_SCOPES = {"ALL", "INCLUDE", "EXCLUDE"}
ALERT_TYPES = {"NEW_LOW", "REAL_DEAL", "PRICE_DROP", "TARGET_PRICE", "BACK_IN_STOCK"}
FILTER_LIST_KEYS = (
    "store", "category", "merchant", "location", "exclude_location",
    "commerce_type", "catalog_domain", "brand", "browse_node",
    "collections", "store_facets",
)


def register_routes(app):
    def _enabled_providers():
        cfg = get_merged_config(None)
        configured = cfg.get("providers", {})
        return [p for p in sorted(KNOWN_PROVIDERS) if configured.get(p, {}).get("enabled", True)]

    def _base_filters(extra=None):
        f = {}
        provider = request.cookies.get('dh_provider', 'all')
        if provider != 'all':
            if provider in _enabled_providers():
                f['providers'] = [provider]
            else:
                # Malformed/disabled preference must never broaden visibility.
                f['providers'] = ['__invalid_provider__']
        if extra:
            f.update(extra)
        return f

    def _query_value(parser, *args, **kwargs):
        try:
            return parser(*args, **kwargs)
        except QueryParamError as exc:
            abort(400, str(exc))

    def _page():
        return _query_value(parse_page, request.args.get('page'))

    def _cursor():
        return _query_value(parse_cursor, request.args.get('cursor'))

    def _sort(allowed, default):
        return _query_value(parse_enum, request.args.get('sort'), name='sort', allowed=allowed, default=default)

    def _catalog_request_filters(extra=None):
        filters = _base_filters(extra)
        for key in FILTER_LIST_KEYS:
            values = [value for value in request.args.getlist(key) if value]
            if values:
                filters[key] = values
        # Modern branch scope uses one location selector. Legacy exclude_location
        # URLs remain accepted and are translated to the same query contract.
        explicit_scope = request.args.get('branch_scope')
        if explicit_scope:
            branch_scope = _query_value(parse_enum, explicit_scope, name='branch_scope', allowed=BRANCH_SCOPES, default='ALL')
        elif filters.get('exclude_location'):
            branch_scope = 'EXCLUDE'
        elif filters.get('location'):
            branch_scope = 'INCLUDE'
        else:
            branch_scope = 'ALL'
        selected_locations = list(filters.get('location') or filters.get('exclude_location') or [])
        filters.pop('location', None)
        filters.pop('exclude_location', None)
        if branch_scope == 'INCLUDE' and selected_locations:
            filters['location'] = selected_locations
        elif branch_scope == 'EXCLUDE' and selected_locations:
            filters['exclude_location'] = selected_locations
        filters['branch_scope'] = branch_scope
        if request.args.get('only_deals'):
            filters['only_deals'] = True
        if request.args.get('min_discount') not in (None, ''):
            filters['min_discount'] = _query_value(
                parse_float, request.args.get('min_discount'), name='min_discount', minimum=0.0, maximum=100.0
            )
        if request.args.get('max_price') not in (None, ''):
            filters['max_price'] = _query_value(
                parse_float, request.args.get('max_price'), name='max_price', minimum=0.0, maximum=1_000_000_000.0
            )
        channel = _query_value(
            parse_enum, request.args.get('channel'), name='channel', allowed=CHANNELS, default='PUBLIC'
        )
        if channel != 'PUBLIC' or request.args.get('channel'):
            filters['channel'] = channel
        return filters

    def _facet_template_args(facets):
        return {
            'av_stores': [{'id': item['filter_key'], 'name': item['name']} for item in facets.get('stores', [])],
            'av_cats': facets.get('categories', []),
            'av_collections': facets.get('collections', []),
            'av_store_facets': facets.get('store_facets', []),
            'av_merchants': facets.get('merchants', []),
            'av_locations': facets.get('locations', []),
            'av_commerce_types': facets.get('commerce_types', []),
            'av_catalog_domains': facets.get('catalog_domains', []),
            'av_brands': facets.get('brands', []),
            'av_browse_nodes': facets.get('browse_nodes', []),
        }

    def _render_catalog_partial(data, filters, sort, current_path=None):
        template = 'partials/catalog_append.html' if request.args.get('cursor') else 'partials/catalog_grid.html'
        return render_template(
            template, data=data, filters=filters, sort=sort,
            view_mode=request.cookies.get('view_mode', 'cards'), current_path=current_path or request.path,
        )

    @app.context_processor
    def provider_context():
        selected = request.cookies.get('dh_provider', 'all')
        enabled = _enabled_providers()
        if selected != 'all' and selected not in enabled:
            selected = 'invalid'
        return {'shopping_providers': enabled, 'selected_provider': selected}

    @app.post('/preferences/provider')
    def select_provider():
        selected = request.form.get('provider', 'all')
        if selected != 'all' and selected not in _enabled_providers():
            abort(400, 'provider has an unsupported or disabled value')
        target = local_redirect_target(
            request.referrer, host=request.host, default=url_for('home')
        )
        response = redirect(target)
        response.set_cookie('dh_provider', selected, max_age=365 * 24 * 3600, samesite='Lax')
        return response

    
    @app.route('/')
    def home():
        db_path = current_app.config['DATABASE']
        metrics = get_home_metrics(db_path)
        deals = get_home_deals(db_path, _base_filters())
        watchlist = get_watchlist(db_path, _base_filters())
        return render_template('home.html', metrics=metrics, deals=deals, watchlist=watchlist, current_path='/')
        
    @app.route('/search')
    def search():
        q = request.args.get('q', '')
        if not q or len(q) < 3:
            if request.headers.get('HX-Request'):
                return "<div>Introduce al menos 3 caracteres</div>"
            return render_template('search_results.html', results={}, q=q, current_path='/search')
            
        db_path = current_app.config['DATABASE']
        results = search_local(db_path, q, _base_filters())
        
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', results=results, q=q)
        return render_template('search_results.html', results=results, q=q, current_path='/search')

    @app.route('/products')
    def products():
        db_path = current_app.config['DATABASE']
        results = search_local(db_path, "", _base_filters())
        return render_template('products.html', results=results, current_path='/products')

    @app.route('/products/<provider>/<store_id>/<product_id>')
    def product_detail(provider, store_id, product_id):
        db_path = current_app.config['DATABASE']
        p = get_product_detail(db_path, provider, store_id, product_id)
        if not p:
            return render_template('404_product.html', current_path='/products'), 404
        return render_template('product_detail.html', p=p, current_path='/products')

    @app.route('/compare')
    def compare():
        store_id = request.args.get('store_id')
        product_id = request.args.get('product_id')
        q = request.args.get('q', '')
        
        db_path = current_app.config['DATABASE']
        
        if store_id and product_id:
            provider = request.args.get('provider')
            res = get_anchor_compare(db_path, provider, store_id, product_id)
            if request.headers.get('HX-Request'):
                return render_template('partials/compare_results_anchor.html', res=res)
            return render_template('compare.html', res=res, anchor_mode=True, current_path='/compare')
        else:
            res = get_product_compare(db_path, q) if q and len(q) >= 3 else []
            if request.headers.get('HX-Request'):
                return render_template('partials/compare_results.html', results=res, q=q)
            return render_template('compare.html', results=res, q=q, anchor_mode=False, current_path='/compare')

    @app.route('/best')
    def best():
        from dealhunter.web.best import get_best_buys
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(BEST_SORTS, 'score')
        category = request.args.getlist('category')
        store_type = request.args.get('store_type', '')
        
        filters = _base_filters()
        if category: filters["category"] = category
        if store_type: filters["store_type"] = store_type
        
        data = get_best_buys(db_path, filters, sort, page)
        
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'), is_best_buys=True)
            
        av_cats = get_available_categories(db_path, store_type if store_type else None)
        return render_template('best.html', data=data, sort=sort, filters={"category": category, "store_type": store_type}, av_cats=av_cats, current_path='/best', is_best_buys=True)


    @app.route('/deals')
    def deals():
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(DEAL_SORTS, 'opportunity')
        tab = _query_value(parse_enum, request.args.get('tab'), name='tab', allowed=DEAL_TABS, default='Todo')
        filters = _base_filters({"tab": tab})
        data = get_deals(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        return render_template('deals.html', data=data, tab=tab, sort=sort, current_path='/deals')
        
    @app.route('/market')
    def market():
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = _catalog_request_filters({"vertical": "market", "commerce_type": ["SUPERMARKET"], "catalog_domain": ["RETAIL"]})
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        facets = get_ui_facets(db_path, filters)
        return render_template('catalog.html', data=data, sort=sort, filters=filters,
                               title="Supermercados", current_path='/market', emoji="🛒",
                               **_facet_template_args(facets))
        
    @app.route('/turbo')
    def turbo():
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = _catalog_request_filters({"vertical": "turbo"})
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        facets = get_ui_facets(db_path, filters)
        return render_template('catalog.html', data=data, sort=sort, filters=filters,
                               title="Rappi Turbo", current_path='/turbo', emoji="⚡",
                               **_facet_template_args(facets))
        

    @app.route('/partials/categories')
    def partial_categories():
        db_path = current_app.config['DATABASE']
        filters = _base_filters()
        if request.args.get('vertical'): filters["vertical"] = request.args.get('vertical')
        if request.args.getlist('store'): filters["store"] = request.args.getlist('store')
        facets = get_ui_facets(db_path, filters)
        av_cats = facets["categories"]
        formatted_cats = [{'id': c, 'name': c} for c in av_cats]
        return render_template('partials/multiselect_options.html', options=formatted_cats, name='category', selected_values=request.args.getlist('category'))

    @app.route('/categories')
    def categories():
        db_path = current_app.config['DATABASE']
        filters = _base_filters()
        browse_cats = get_browse_categories(db_path, filters)
        raw_cats = get_categories(db_path, filters)
        return render_template('categories.html', cats=browse_cats, raw_cats=raw_cats, current_path='/categories')

    @app.route('/categories/browse/<node_id>')
    def browse_category_detail(node_id):
        db_path = current_app.config['DATABASE']
        node = get_browse_node(db_path, node_id)
        if not node:
            abort(404)
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = _catalog_request_filters({"browse_node": [node_id]})
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        facets = get_ui_facets(db_path, filters)
        return render_template('catalog.html', data=data, sort=sort, filters=filters,
                               title=f"Categoría: {node['name']}", current_path='/categories', emoji="📦",
                               **_facet_template_args(facets))

    @app.route('/categories/<category>')
    def category_detail(category):
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = _catalog_request_filters({"category": category})
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        facets = get_ui_facets(db_path, filters)
        return render_template('catalog.html', data=data, sort=sort, filters=filters,
                               title=f"Categoría: {category}", current_path='/categories', emoji="📦",
                               **_facet_template_args(facets))
        
    @app.route('/stores')
    def stores():
        db_path = current_app.config['DATABASE']
        show_all = request.args.get('all', '0') == '1'
        filters = _base_filters()
        merchants = get_merchants_directory(db_path, filters=filters)
        unmapped = get_stores(
            db_path, hide_empty=not show_all, filters=filters, unmapped_only=True
        )
        return render_template(
            'stores.html', merchants=merchants, stores=unmapped,
            current_path='/stores', show_all=show_all,
        )
        
    @app.route('/stores/<provider>/<store_id>')
    def store_detail(provider, store_id):
        db_path = current_app.config['DATABASE']
        detail = get_store_detail(db_path, provider, store_id)
        if not detail:
            return "Store not found", 404
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = {"provider": provider, "store": f"{provider}::{store_id}"}
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return _render_catalog_partial(data, filters, sort)
        return render_template('store_detail.html', detail=detail, data=data, sort=sort, filters=filters, current_path='/stores')


    

    from dealhunter.web.queries import get_restaurants_home, get_restaurant_detail

    @app.route('/restaurants')
    def restaurants():
        db_path = current_app.config['DATABASE']
        page = _page()
        sort = _sort(CATALOG_SORTS, 'discount')
        filters = _catalog_request_filters({"commerce_type": ["RESTAURANT"], "catalog_domain": ["MENU"]})
        data = get_catalog(db_path, filters, sort, page, cursor=_cursor())
        
        if request.headers.get('HX-Request'):
            return _render_catalog_partial(data, filters, sort, current_path='/restaurants')
            
        facets = get_ui_facets(db_path, filters)
        return render_template('catalog.html', data=data, sort=sort, filters=filters,
                               title="Restaurantes", current_path='/restaurants', emoji="🍔",
                               **_facet_template_args(facets))
        
    @app.route('/restaurants/<provider>/<store_id>')
    def restaurant_detail(provider, store_id):
        db_path = current_app.config['DATABASE']
        detail = get_restaurant_detail(db_path, provider, store_id)
        if not detail:
            return "Restaurant not found", 404
        return render_template('restaurant_detail.html', detail=detail, current_path='/restaurants')

    @app.route('/watchlist')
    def watchlist_view():
        db_path = current_app.config['DATABASE']
        items = get_watchlist(db_path, _base_filters())
        return render_template('watchlist.html', items=items, current_path='/watchlist')
    
    @app.route('/alerts')
    def alerts():
        from dealhunter.alerts import AlertEngine
        db_path = current_app.config['DATABASE']
        alert_type = _query_value(parse_enum, request.args.get('type'), name='type', allowed=ALERT_TYPES, default=None)
        alerts_data = AlertEngine.read_alerts(db_path, top=200, alert_type=alert_type)
        return render_template('alerts.html', alerts=alerts_data, selected_type=alert_type, alert_types=sorted(ALERT_TYPES), current_path='/alerts')
    

    @app.route('/api/open-rappi', methods=['POST'])
    def open_rappi():
        from dealhunter.web.rappi_native import (
            RappiNavigationBusy,
            RappiNavigationError,
            UnsupportedStoreType,
            open_store_in_rappi,
        )

        store_id = request.form.get("store_id")
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        def _error(msg, code=400):
            if is_ajax:
                return jsonify({"ok": False, "error": msg}), code
            flash(msg, "danger")
            return redirect(local_redirect_target(request.referrer, host=request.host, default=url_for('home')))

        def _success(msg):
            if is_ajax:
                return jsonify({"ok": True, "message": msg})
            flash(msg, "success")
            return redirect(local_redirect_target(request.referrer, host=request.host, default=url_for('home')))

        if not store_id or not store_id.isdigit():
            return _error("Falta ID de tienda válido.")

        # CSRF is validated by the before_request middleware in app.py.
        # Store metadata is resolved server-side; the client supplies only its ID.
        import sqlite3
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            row = conn.execute(
                "SELECT name, type FROM stores WHERE provider = 'rappi' AND store_id = ?",
                (store_id,),
            ).fetchone()
        if row is None:
            return _error("La tienda no existe en DealHunter.", 404)

        try:
            open_store_in_rappi(store_id, row[1])
        except UnsupportedStoreType:
            return _error("Este tipo de tienda no tiene navegación nativa verificada.", 422)
        except RappiNavigationBusy:
            return _error("Rappi ya está procesando otra navegación.", 409)
        except RappiNavigationError:
            return _error(
                "No fue posible abrir la tienda exacta en Rappi. "
                "Verifica que Shizuku esté activo y Termux autorizado.",
                502,
            )

        return _success("✓ Tienda exacta abierta en la app de Rappi")

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('placeholder.html', title="404 - No Encontrado", subtitle="La página que buscas no existe.", current_path=""), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('placeholder.html', title="Error Interno", subtitle="No pudimos leer los datos.\nCódigo: DB_ERROR\nTus datos no fueron modificados.", current_path=""), 500
