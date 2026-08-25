from flask import render_template, request, current_app, redirect, url_for, flash, jsonify
from dealhunter.web.queries import (
    get_home_metrics, get_home_deals, get_watchlist, search_local, 
    get_product_detail, get_product_compare, get_anchor_compare,
    get_deals, get_catalog, get_categories, get_stores, get_store_detail, get_available_stores, get_available_categories, get_ui_facets
)

def register_routes(app):
    def _base_filters(extra=None):
        f = {}
        provider = request.cookies.get('dh_provider', 'all')
        if provider != 'all':
            f['providers'] = [provider]
        if extra:
            f.update(extra)
        return f

    
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
        results = search_local(db_path, "")
        return render_template('products.html', results=results, current_path='/products')

    @app.route('/products/<store_id>/<product_id>')
    def product_detail(store_id, product_id):
        db_path = current_app.config['DATABASE']
        p = get_product_detail(db_path, store_id, product_id)
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
            res = get_anchor_compare(db_path, store_id, product_id)
            if request.headers.get('HX-Request'):
                return render_template('partials/compare_results_anchor.html', res=res)
            return render_template('compare.html', res=res, anchor_mode=True, current_path='/compare')
        else:
            res = get_product_compare(db_path, q) if q and len(q) >= 3 else []
            if request.headers.get('HX-Request'):
                return render_template('partials/compare_results.html', results=res, q=q)
            return render_template('compare.html', results=res, q=q, anchor_mode=False, current_path='/compare')

    @app.route('/deals')
    
    @app.route('/best')
    def best():
        from dealhunter.web.best import get_best_buys
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'score')
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
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        tab = request.args.get('tab', 'Todo')
        data = get_deals(db_path, _base_filters({"tab": tab}), sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'))
        return render_template('deals.html', data=data, tab=tab, sort=sort, current_path='/deals')
        
    @app.route('/market')
    def market():
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        store = request.args.getlist('store')
        category = request.args.getlist('category')
        filters = {"vertical": "market"}
        if store: filters["store"] = store
        if category: filters["category"] = category
        if request.args.get('only_deals'): filters['only_deals'] = True
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'))
        facets = get_ui_facets(db_path, filters)
        av_stores = [{"id": s["store_id"], "name": s["name"]} for s in facets["stores"]]
        av_cats = facets["categories"]
        return render_template('catalog.html', data=data, sort=sort, filters=filters, av_stores=av_stores, av_cats=av_cats, av_collections=facets.get('collections', []), av_store_facets=facets.get('store_facets', []), title="Supermercados", current_path='/market', emoji="🛒").replace('av_cats=av_cats, ', 'av_cats=av_cats, av_collections=facets.get(\"collections\", []), av_store_facets=facets.get(\"store_facets\", []), ')
        
    @app.route('/turbo')
    def turbo():
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        store = request.args.getlist('store')
        category = request.args.getlist('category')
        filters = {"vertical": "turbo"}
        if store: filters["store"] = store
        if category: filters["category"] = category
        if request.args.get('only_deals'): filters['only_deals'] = True
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'))
        facets = get_ui_facets(db_path, filters)
        av_stores = [{"id": s["store_id"], "name": s["name"]} for s in facets["stores"]]
        av_cats = facets["categories"]
        return render_template('catalog.html', data=data, sort=sort, filters=filters, av_stores=av_stores, av_cats=av_cats, av_collections=facets.get('collections', []), av_store_facets=facets.get('store_facets', []), title="Rappi Turbo", current_path='/turbo', emoji="⚡").replace('av_cats=av_cats, ', 'av_cats=av_cats, av_collections=facets.get(\"collections\", []), av_store_facets=facets.get(\"store_facets\", []), ')
        

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
        cats = get_categories(db_path, _base_filters())
        return render_template('categories.html', cats=cats, current_path='/categories')
        
    @app.route('/categories/<category>')
    def category_detail(category):
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        store = request.args.getlist('store')
        filters = {"category": category}
        if store: filters["store"] = store
        if request.args.get('only_deals'): filters['only_deals'] = True
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'))
        facets = get_ui_facets(db_path, filters)
        av_stores = [{"id": s["store_id"], "name": s["name"]} for s in facets["stores"]]
        av_cats = facets["categories"]
        return render_template('catalog.html', data=data, sort=sort, filters=filters, av_stores=av_stores, av_cats=av_cats, av_collections=facets.get('collections', []), av_store_facets=facets.get('store_facets', []), title=f"Categoría: {category}", current_path='/categories', emoji="📦").replace('av_cats=av_cats, ', 'av_cats=av_cats, av_collections=facets.get(\"collections\", []), av_store_facets=facets.get(\"store_facets\", []), ')
        
    @app.route('/stores')
    def stores():
        db_path = current_app.config['DATABASE']
        show_all = request.args.get('all', '0') == '1'
        stores_list = get_stores(db_path, hide_empty=not show_all)
        return render_template('stores.html', stores=stores_list, current_path='/stores', show_all=show_all)
        
    @app.route('/stores/<store_id>')
    def store_detail(store_id):
        db_path = current_app.config['DATABASE']
        detail = get_store_detail(db_path, store_id)
        if not detail:
            return "Store not found", 404
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        filters = {"store": store_id}
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, view_mode=request.cookies.get('view_mode', 'cards'))
        return render_template('store_detail.html', detail=detail, data=data, sort=sort, filters=filters, current_path='/stores')


    

    from dealhunter.web.queries import get_restaurants_home, get_restaurant_detail

    @app.route('/restaurants')
    def restaurants():
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'discount')
        store = request.args.getlist('store')
        category = request.args.getlist('category')
        filters = {"vertical": "restaurants"}
        if store: filters["store"] = store
        if category: filters["category"] = category
        if request.args.get('only_deals'): filters['only_deals'] = True
        data = get_catalog(db_path, filters, sort, page)
        
        if request.headers.get('HX-Request'):
            return render_template('partials/catalog_grid.html', data=data, filters=filters, sort=sort, current_path='/restaurants')
            
        facets = get_ui_facets(db_path, filters)
        av_stores = [{"id": s["store_id"], "name": s["name"]} for s in facets["stores"]]
        av_cats = facets["categories"]
        return render_template('catalog.html', data=data, sort=sort, filters=filters, av_stores=av_stores, av_cats=av_cats, av_collections=facets.get('collections', []), av_store_facets=facets.get('store_facets', []), title="Restaurantes", current_path='/restaurants', emoji="🍔").replace('av_cats=av_cats, ', 'av_cats=av_cats, av_collections=facets.get(\"collections\", []), av_store_facets=facets.get(\"store_facets\", []), ')
        
    @app.route('/restaurants/<store_id>')
    def restaurant_detail(store_id):
        db_path = current_app.config['DATABASE']
        detail = get_restaurant_detail(db_path, store_id)
        if not detail:
            return "Restaurant not found", 404
        return render_template('restaurant_detail.html', detail=detail, current_path='/restaurants')

    @app.route('/watchlist')
    def watchlist_view(): return render_template('placeholder.html', title="Watchlist", current_path='/watchlist')
    
    @app.route('/alerts')
    def alerts(): return render_template('placeholder.html', title="Alertas", current_path='/alerts')
    

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
            return redirect(request.referrer or url_for('home'))

        def _success(msg):
            if is_ajax:
                return jsonify({"ok": True, "message": msg})
            flash(msg, "success")
            return redirect(request.referrer or url_for('home'))

        if not store_id or not store_id.isdigit():
            return _error("Falta ID de tienda válido.")

        # CSRF is validated by the before_request middleware in app.py.
        # Store metadata is resolved server-side; the client supplies only its ID.
        import sqlite3
        with sqlite3.connect(current_app.config['DATABASE']) as conn:
            row = conn.execute(
                "SELECT name, type FROM stores WHERE store_id = ?",
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

