import os
from urllib.parse import urlparse
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
        parsed_url = urlparse(turso_url)
        host = parsed_url.netloc or parsed_url.path.replace('libsql://', '').strip('/')
        
        SQLALCHEMY_DATABASE_URI = f"sqlite+libsql://{host}?secure=true"
        
        # ✅ FIX: Bỏ "timeout" vì libsql không hỗ trợ tham số này trong connect_args
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "auth_token": turso_token
            },
            "pool_pre_ping": True,
            "pool_recycle": 280, 
        }
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TIMEZONE = 'Asia/Ho_Chi_Minh'

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_SECURE = True 
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')