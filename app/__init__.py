import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    Migrate(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = None
    login_manager.login_message_category = 'info'

    os.makedirs(os.path.join(app.root_path, 'static', 'models'), exist_ok=True)

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
    app.register_blueprint(api_bp) # Phải có dòng này

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    return app

from app.models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))