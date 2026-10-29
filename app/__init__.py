import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_caching import Cache
from flask_compress import Compress
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
cache = Cache()
compress = Compress()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # --- REDIS FALLBACK AN TOÀN ---
    redis_url = os.environ.get('REDIS_URL')
    cache_config = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 10,
    }
    
    if redis_url:
        if redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
            
        if redis_url.startswith('rediss://'):
            try:
                test_cfg = {
                    'CACHE_TYPE': 'RedisCache',
                    'CACHE_REDIS_URL': redis_url,
                    'CACHE_DEFAULT_TIMEOUT': 10,
                    'CACHE_OPTIONS': { 'ssl_cert_reqs': 'none' }
                }
                probe = Cache()
                probe.init_app(app, config=test_cfg)
                probe.get('__probe__')
                cache_config = test_cfg
                print("[Cache] Đang sử dụng Upstash Redis (TLS).")
            except Exception as e:
                print(f"[Cache] Redis không khả dụng ({e}). Fallback SimpleCache.")
        else:
            print("[Cache] Link Redis không đúng định dạng (phải là rediss://).")
    else:
        print("[Cache] Không tìm thấy REDIS_URL hợp lệ. Sử dụng SimpleCache.")
        
    cache.init_app(app, config=cache_config)

    # --- NÉN GZIP/BROTLI ---
    compress.init_app(app)
    app.config['COMPRESS_ALGORITHM'] = ['br', 'gzip']
    app.config['COMPRESS_BR_LEVEL'] = 4
    app.config['COMPRESS_LEVEL'] = 6

    Migrate(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = None
    login_manager.login_message_category = 'info'

    os.makedirs(os.path.join(app.root_path, 'static', 'models'), exist_ok=True)

    # ==================== ĐĂNG KÝ BLUEPRINTS ====================
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
    
    # ✅ ĐĂNG KÝ BLUEPRINT WALLET
    from app.routes.wallet import bp as wallets_bp
    app.register_blueprint(wallets_bp)
    
    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    @app.after_request
    def add_cache_headers(response):
        if request.path.startswith('/static/'):
            if '/css/style.css' in request.path or '/js/main.js' in request.path:
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            else:
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path.startswith('/api/') or request.path == '/':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    return app


# Load user an toàn
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)