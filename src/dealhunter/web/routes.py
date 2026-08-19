from flask import render_template, request, current_app
from dealhunter.web.queries import get_home_metrics, get_home_deals, get_watchlist, search_local

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
            return render_template('search_results.html', results={}, q=q)
            
        db_path = current_app.config['DATABASE']
        results = search_local(db_path, q)
        
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', results=results, q=q)
        return render_template('search_results.html', results=results, q=q, current_path='/search')

    # Placeholders
    @app.route('/deals')
    def deals(): return render_template('placeholder.html', title="Deals", current_path='/deals')
    
    @app.route('/market')
    def market(): return render_template('placeholder.html', title="Supermercados", current_path='/market')
    
    @app.route('/turbo')
    def turbo(): return render_template('placeholder.html', title="Turbo", current_path='/turbo')
    
    @app.route('/restaurants')
    def restaurants(): return render_template('placeholder.html', title="Restaurantes", current_path='/restaurants')
    
    @app.route('/categories')
    def categories(): return render_template('placeholder.html', title="Categorías", current_path='/categories')
    
    @app.route('/products')
    def products(): return render_template('placeholder.html', title="Productos", current_path='/products')
    
    @app.route('/stores')
    def stores(): return render_template('placeholder.html', title="Tiendas", current_path='/stores')
    
    @app.route('/compare')
    def compare(): return render_template('placeholder.html', title="Comparar", current_path='/compare')
    
    @app.route('/watchlist')
    def watchlist_view(): return render_template('placeholder.html', title="Watchlist", current_path='/watchlist')
    
    @app.route('/alerts')
    def alerts(): return render_template('placeholder.html', title="Alertas", current_path='/alerts')
    
    @app.route('/admin')
    def admin(): return render_template('placeholder.html', title="Sistema", current_path='/admin')
    
    @app.route('/admin/account')
    def admin_account(): return render_template('placeholder.html', title="Cuenta Rappi", subtitle="Diagnóstico read-only. DealHunter nunca almacena tokens de sesión.", current_path='/admin/account')

    # Handle 404
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('placeholder.html', title="404 - No Encontrado", subtitle="La página que buscas no existe.", current_path=""), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        return render_template('placeholder.html', title="Error Interno", subtitle="No pudimos leer los datos.\nCódigo: DB_ERROR\nTus datos no fueron modificados.", current_path=""), 500
