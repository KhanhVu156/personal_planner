import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from datetime import timedelta

# =========================================================
# 1. KHỞI TẠO MÔI TRƯỜNG (ENVIRONMENT SETUP)
# =========================================================
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# Xác định môi trường hiện tại (Local hay Production)
FLASK_ENV = os.environ.get('FLASK_ENV', 'development').lower()
IS_PRODUCTION = (FLASK_ENV == 'production')


class Config:
    """
    Cấu hình trung tâm cho toàn bộ ứng dụng.
    
    TƯ DUY THIẾT KẾ:
    - Phân tách rõ ràng cấu hình cho từng môi trường (Local vs Production).
    - Sử dụng biến môi trường cho các dữ liệu nhạy cảm (Không hardcode).
    - Tối ưu hóa giới hạn tài nguyên để chống tấn công DoS (Denial of Service).
    """
    
    # =========================================================
    # A. CẤU HÌNH BẢO MẬT CỐT LÕI (CORE SECURITY)
    # =========================================================
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # TƯ DUY BẢO MẬT: Nếu chạy Production mà thiếu SECRET_KEY thì phải chặn ngay lập tức
    # để tránh việc app chạy với key mặc định (rất dễ bị hack session).
    if IS_PRODUCTION and not SECRET_KEY:
        raise ValueError("CRITICAL: SECRET_KEY phải được thiết lập trên môi trường Production!")
    SECRET_KEY = SECRET_KEY or 'dev-key-not-for-production-123'

    # ✅ TƯ DUY BẢO MẬT: Giới hạn dung lượng file upload (VD: tối đa 5MB).
    # Tránh việc kẻ xấu upload file CSV nặng hàng trăm MB làm tràn RAM Server.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    # =========================================================
    # B. CẤU HÌNH DATABASE (TURSO vs LOCAL SQLITE)
    # =========================================================
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')

    if turso_url and turso_token:
        # --- PRODUCTION: Turso Cloud Database ---
        parsed_url = urlparse(turso_url)
        host = parsed_url.netloc or parsed_url.path.replace('libsql://', '').strip('/')
        
        SQLALCHEMY_DATABASE_URI = f"sqlite+libsql://{host}?secure=true"
        
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"auth_token": turso_token},
            # TƯ DUY: pool_recycle 280s để chủ động gia hạn connection, 
            # tránh bị Cloud DB tự động ngắt kết nối (idle timeout) gây lỗi Broken Pipe.
            "pool_pre_ping": True,
            "pool_recycle": 280, 
        }
    else:
        # --- LOCAL: SQLite File ---
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            # TƯ DUY: Bật check_same_thread=False cho phép SQLite xử lý đa luồng (Gunicorn threads)
            "connect_args": {"check_same_thread": False}
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================================================
    # C. CẤU HÌNH SESSION & COOKIES (BẢO MẬT & UX)
    # =========================================================
    TIMEZONE = 'Asia/Ho_Chi_Minh'

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # ✅ FIX CRITICAL: Chỉ bật Secure Cookie khi chạy HTTPS (Production).
    # Nếu bật ở Local (HTTP), trình duyệt sẽ từ chối lưu Cookie -> Không thể đăng nhập.
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # =========================================================
    # D. CẤU HÌNH MAIL (GỬI EMAIL NHẮC NHỞ)
    # =========================================================
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')