from flask import render_template, request, current_app, redirect, url_for, flash, jsonify
from dealhunter.web.queries import (
    get_home_metrics, get_home_deals, get_watchlist, search_local, 
    get_product_detail, get_product_compare, get_anchor_compare,
    get_deals, get_catalog, get_categories, get_stores, get_store_detail, get_available_stores, get_available_categories
)

def register_routes(app):
    
    @app.route('/')
    def home():
        db_path = current_app.config['DATABASE']
        metrics = get_home_metrics(db_path)
        deals = get_home_deals(db_path)
        watchlist = get_watchlist(db_path)
        return render_template('home.html', metrics=metrics, deals=deals, watchlist=watchlist, current_path='/')
        
    @app.route('/search')
    def search():
        q = request.args.get('q', '')
        if not q or len(q) < 3:
            if request.headers.get('HX-Request'):
                return "<div>Introduce al menos 3 caracteres</div>"
            return render_template('search_results.html', results={}, q=q, current_path='/search')
            
        db_path = current_app.config['DATABASE']
        results = search_local(db_path, q)
        
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', results=results, q=q)
        return render_template('search_results.html', results=results, q=q, current_path='/search')

    @app.route('/products')
    def products():
        db_path = current_app.config['DATABASE']
        results = search_local(db_path, "", limit=50)
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
        
        filters = {}
        if category: filters["category"] = category
        if store_type: filters["store_type"] = store_type
        
        data = get_best_buys(db_path, filters, sort, page)
        
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'), is_best_buys=True)
            
        return render_template('best.html', data=data, sort=sort, filters={"category": category, "store_type": store_type}, current_path='/best', is_best_buys=True)


    @app.route('/deals')
    def deals():
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        tab = request.args.get('tab', 'Todo')
        data = get_deals(db_path, {"tab": tab}, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
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
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
        av_stores = get_available_stores(db_path, "market")
        av_cats = get_available_categories(db_path, "market", store)
        return render_template('catalog.html', data=data, sort=sort, filters=filters, av_stores=av_stores, av_cats=av_cats, title="Supermercados", current_path='/market', emoji="🛒")
        
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
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
        return render_template('catalog.html', data=data, sort=sort, filters=filters, title="Rappi Turbo", current_path='/turbo', emoji="⚡")
        
    @app.route('/categories')
    def categories():
        db_path = current_app.config['DATABASE']
        cats = get_categories(db_path)
        return render_template('categories.html', cats=cats, current_path='/categories')
        
    @app.route('/categories/<category>')
    def category_detail(category):
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        filters = {"category": category}
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
        return render_template('catalog.html', data=data, sort=sort, filters=filters, title=f"Categoría: {category}", current_path='/categories', emoji="📦")
        
    @app.route('/stores')
    def stores():
        db_path = current_app.config['DATABASE']
        stores_list = get_stores(db_path)
        return render_template('stores.html', stores=stores_list, current_path='/stores')
        
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
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
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
            return render_template('partials/catalog_grid.html', data=data, current_path='/restaurants')
            
        return render_template('catalog.html', data=data, sort=sort, filters=filters, title="Restaurantes", current_path='/restaurants', emoji="🍔")
        
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
    

    # --- Rappi App Launcher Configuration ---
    # Verified package on this device. Do NOT accept from client.
    RAPPI_PACKAGE = "com.grability.rappi"
    RAPPI_URL_HOSTS = {"www.rappi.com.mx"}

    @app.route('/api/open-rappi', methods=['POST'])
    def open_rappi():
        import subprocess
        import shutil

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

        # CSRF is validated by the before_request middleware in app.py
        # Resolve store type server-side
        import sqlite3
        conn = sqlite3.connect(current_app.config['DATABASE'])
        c = conn.cursor()
        c.execute("SELECT type FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        store_type = row[0] if row else ""

        is_restaurant = store_type in ("restaurant", "restaurants")

        if is_restaurant:
            url = f"https://www.rappi.com.mx/restaurantes/{store_id}"
        else:
            url = f"https://www.rappi.com.mx/tiendas/{store_id}"

        # Verify am is available
        if not shutil.which("am"):
            return _error("El comando 'am' no está disponible en este entorno.")

        # Attempt 1: Directed Intent with package targeting + store URL
        try:
            result = subprocess.run(
                ["am", "start", "-a", "android.intent.action.VIEW",
                 "-d", url, "-p", RAPPI_PACKAGE],
                capture_output=True, text=True, timeout=5, shell=False
            )
            if result.returncode == 0 and "Error" not in (result.stdout or ""):
                return _success("✓ Tienda abierta en la app de Rappi")
        except Exception:
            pass

        # Attempt 2: Open Rappi app to home screen (package works, deep link doesn't)
        try:
            result = subprocess.run(
                ["am", "start", "-a", "android.intent.action.MAIN",
                 "-c", "android.intent.category.LAUNCHER",
                 "-p", RAPPI_PACKAGE],
                capture_output=True, text=True, timeout=5, shell=False
            )
            if result.returncode == 0 and "Error" not in (result.stdout or ""):
                return _success(
                    "✓ App de Rappi abierta. "
                    "La tienda no pudo abrirse directamente — "
                    "busca manualmente en la app."
                )
        except Exception:
            pass

        # All attempts failed — Rappi not installed or not reachable
        return _error("No fue posible abrir esta tienda en la app de Rappi. "
                       "Verifica que Rappi esté instalada.")

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('placeholder.html', title="404 - No Encontrado", subtitle="La página que buscas no existe.", current_path=""), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('placeholder.html', title="Error Interno", subtitle="No pudimos leer los datos.\nCódigo: DB_ERROR\nTus datos no fueron modificados.", current_path=""), 500


