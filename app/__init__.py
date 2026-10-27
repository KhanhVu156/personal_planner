import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_caching import Cache
from flask_compress import Compress # Thêm import này
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
cache = Cache()
compress = Compress() # Khởi tạo Compress

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # CẤU HÌNH UPSTASH REDIS CACHE
    cache.init_app(app, config={
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'CACHE_DEFAULT_TIMEOUT': 10 
    })

    # ---- LEVEL 4: BẬT NÉN GZIP/BROTLI ----
    compress.init_app(app)
    app.config['COMPRESS_ALGORITHM'] = ['br', 'gzip'] # Ưu tiên Brotli
    app.config['COMPRESS_BR_LEVEL'] = 4               # Mức nén Brotli (0-11)
    app.config['COMPRESS_LEVEL'] = 6                  # Mức nén Gzip (0-9)
    # -------------------------------------

    Migrate(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = None
    login_manager.login_message_category = 'info'

    os.makedirs(os.path.join(app.root_path, 'static', 'models'), exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'cache'), exist_ok=True)

    # Đăng ký các Blueprint
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.transactions import bp as transactions_bp
    app.register_blueprint(transactions_bp)

    from app.routes.budgets import bp as budgets_bp
    app.register_blueprint(budgets_bp)

    from app.routes.tasks import bp as tasks_bp
    app.register_blueprint(tasks_bp)
    
    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    # CẤU HÌNH HTTP CACHING (LEVEL 3 - PHẦN 2)
    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path.startswith('/api/') or request.path == '/':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    return app

from app.models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))