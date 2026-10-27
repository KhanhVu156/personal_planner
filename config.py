import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-prod'
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CẤU HÌNH QUAN TRỌNG CHO RENDER: 
    # Tránh lỗi "server closed the connection unexpectedly" do Render ngắt kết nối rảnh rỗi
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,     # Tự động kiểm tra kết nối trước khi dùng
        "pool_recycle": 280,       # Tự động tạo kết nối mới sau 280 giây
    }
    
    # Cấu hình thời gian
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2) 
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    # Cấu hình bảo mật (Bắt buộc cho Production)
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')