import os
from flask import Flask
from dealhunter.db import get_default_db_path
from dealhunter.web.routes import register_routes

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=get_default_db_path(),
    )
    
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
        
    register_routes(app)
    
    return app

def run_server(port=8765, debug=False):
    app = create_app()
    app.run(host='127.0.0.1', port=port, debug=debug)
