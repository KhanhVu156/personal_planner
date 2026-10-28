import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-prod'

    # --- CẤU HÌNH TURSO (CHỈ KHI CÓ BIẾN MÔI TRƯỜNG) ---
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')

    if turso_url and turso_token:
        # Trên Render (Linux): dùng Turso
        db_url = turso_url.replace('libsql://', '')
        SQLALCHEMY_DATABASE_URI = f"sqlite+libsql://{db_url}/?authToken={turso_token}&secure=true"
    else:
        # Dưới Windows (local): dùng SQLite file
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    # ------------------------------------------------

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')