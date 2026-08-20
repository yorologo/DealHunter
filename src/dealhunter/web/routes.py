from flask import render_template, request, current_app
from dealhunter.web.queries import (
    get_home_metrics, get_home_deals, get_watchlist, search_local, 
    get_product_detail, get_product_compare, get_anchor_compare,
    get_deals, get_catalog, get_categories, get_stores, get_store_detail
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
        store = request.args.get('store', '')
        category = request.args.get('category', '')
        filters = {"vertical": "market"}
        if store: filters["store"] = store
        if category: filters["category"] = category
        data = get_catalog(db_path, filters, sort, page)
        if request.headers.get('HX-Request') and not request.headers.get('HX-Boosted'):
            return render_template('partials/catalog_grid.html', data=data, view_mode=request.cookies.get('view_mode', 'cards'))
        return render_template('catalog.html', data=data, sort=sort, filters=filters, title="Supermercados", current_path='/market', emoji="🛒")
        
    @app.route('/turbo')
    def turbo():
        db_path = current_app.config['DATABASE']
        page = int(request.args.get('page', 1))
        sort = request.args.get('sort', 'opportunity')
        store = request.args.get('store', '')
        category = request.args.get('category', '')
        filters = {"vertical": "turbo"}
        if store: filters["store"] = store
        if category: filters["category"] = category
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
        stores = get_restaurants_home(db_path)
        return render_template('restaurants.html', stores=stores, current_path='/restaurants')
        
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
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('placeholder.html', title="404 - No Encontrado", subtitle="La página que buscas no existe.", current_path=""), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('placeholder.html', title="Error Interno", subtitle="No pudimos leer los datos.\nCódigo: DB_ERROR\nTus datos no fueron modificados.", current_path=""), 500
