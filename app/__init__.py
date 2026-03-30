from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from config import Config
from app.models import db, User

login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import auth, dashboard, transactions, budgets, tasks, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(transactions.bp)
    app.register_blueprint(budgets.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(api.bp)

    from app.tasks import check_deadlines, check_budgets
    scheduler.add_job(func=check_deadlines, trigger="interval", hours=1)
    scheduler.add_job(func=check_budgets, trigger="interval", hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

    return app