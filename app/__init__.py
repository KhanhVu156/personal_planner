import os
from flask import Flask, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_caching import Cache
from flask_compress import Compress
from flask_apscheduler import APScheduler
from config import Config

# TƯ DUY TỐI ƯU: Import Brevo SDK thay vì Flask-Mail
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
cache = Cache()
compress = Compress()

# TƯ DUY KIẾN TRÚC: Đặt tên biến là 'apscheduler' thay vì 'scheduler' để tránh xung đột (Namespace Collision).
# Lý do: Chúng ta có một module tên là 'app/scheduler.py'. Nếu đặt tên biến là 'scheduler', 
# khi import module đó, Python sẽ ghi đè biến instance bằng module, gây lỗi 'module has no attribute add_job'.
apscheduler = APScheduler()

# Biến toàn cục lưu Brevo API instance
brevo_api_instance = None

def send_email(subject, recipient, html_content, text_content=None):
    """
    TƯ DUY TỐI ƯU: Hàm tiện ích dùng chung để gửi email qua Brevo API.
    - Trả về True nếu gửi thành công, False nếu thất bại.
    - Xử lý bắt lỗi (try-except) để không làm sập ứng dụng nếu API gặp sự cố.
    - Tự động lấy cấu hình người gửi từ Config.
    """
    global brevo_api_instance
    
    if not brevo_api_instance:
        current_app.logger.error("[Email] Brevo API chưa được khởi tạo. Không thể gửi mail.")
        return False

    sender_email = current_app.config.get('MAIL_DEFAULT_SENDER')
    sender_name = current_app.config.get('MAIL_DEFAULT_SENDER_NAME', 'Personal Planner')

    # Xây dựng payload cho API Brevo
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": recipient}],
        sender={"email": sender_email, "name": sender_name},
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )

    try:
        api_response = brevo_api_instance.send_transac_email(send_smtp_email)
        current_app.logger.info(f"[Email] Đã gửi thành công đến {recipient}. Message ID: {api_response.message_id}")
        return True
    except ApiException as e:
        current_app.logger.error(f"[Email] Lỗi Brevo API khi gửi đến {recipient}: {e}")
        return False
    except Exception as e:
        current_app.logger.error(f"[Email] Lỗi không xác định khi gửi đến {recipient}: {e}")
        return False


def create_app(config_class=Config):
    global brevo_api_instance
    
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Khởi tạo các extension
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # TƯ DUY TỐI ƯU: Cấu hình Brevo Client
    brevo_api_key = app.config.get('BREVO_API_KEY')
    if brevo_api_key:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = brevo_api_key
        api_client = sib_api_v3_sdk.ApiClient(configuration)
        brevo_api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)
        app.logger.info("[Email] Đã khởi tạo Brevo API Client thành công.")
    else:
        app.logger.warning("[Email] Không tìm thấy BREVO_API_KEY. Chức năng gửi mail sẽ không hoạt động.")

    # --- CẤU HÌNH REDIS FALLBACK AN TOÀN ---
    # TƯ DUY: Ưu tiên dùng Redis để cache. Nếu lỗi (mất mạng, sai pass), 
    # tự động fallback về SimpleCache (RAM) để app không bị crash.
    redis_url = os.environ.get('REDIS_URL')
    cache_config = {
        'CACHE_TYPE': 'SimpleCache', # Mặc định là RAM
        'CACHE_DEFAULT_TIMEOUT': 10,
    }
    
    if redis_url:
        # Upstash yêu cầu TLS (rediss://) thay vì redis://
        if redis_url.startswith('redis://'):
            redis_url = redis_url.replace('redis://', 'rediss://', 1)
            
        if redis_url.startswith('rediss://'):
            try:
                test_cfg = {
                    'CACHE_TYPE': 'RedisCache',
                    'CACHE_REDIS_URL': redis_url,
                    'CACHE_DEFAULT_TIMEOUT': 10,
                    # Bỏ qua kiểm tra chứng chỉ SSL nghiêm ngặt của Upstash để tránh lỗi timeout
                    'CACHE_OPTIONS': {'ssl_cert_reqs': 'none'} 
                }
                probe = Cache()
                probe.init_app(app, config=test_cfg)
                probe.get('__probe__') # Test kết nối thực tế
                cache_config = test_cfg
                app.logger.info("[Cache] Đang sử dụng Upstash Redis (TLS).")
            except Exception as e:
                app.logger.warning(f"[Cache] Redis không khả dụng ({e}). Fallback SimpleCache.")
        else:
            app.logger.warning("[Cache] Link Redis không đúng định dạng (phải là rediss://).")
    else:
        app.logger.info("[Cache] Không tìm thấy REDIS_URL hợp lệ. Sử dụng SimpleCache.")
        
    cache.init_app(app, config=cache_config)

    # --- NÉN GZIP/BROTLI ---
    compress.init_app(app)
    app.config['COMPRESS_ALGORITHM'] = ['br', 'gzip']
    app.config['COMPRESS_BR_LEVEL'] = 4
    app.config['COMPRESS_LEVEL'] = 6

    Migrate(app, db)

    # Cấu hình Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = None 
    login_manager.login_message_category = 'info'

    os.makedirs(os.path.join(app.root_path, 'static', 'models'), exist_ok=True)

    # ==================== ĐĂNG KÝ BLUEPRINTS ====================
    # Đăng ký blueprint main để xử lý trang chủ (Landing Page)
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

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
    
    from app.routes.wallet import bp as wallets_bp
    app.register_blueprint(wallets_bp)
    
    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    @app.after_request
    def add_cache_headers(response):
        """
        TƯ DUY: Tối ưu Cache cho trình duyệt.
        - Static files: Cache dài hạn (1 năm).
        - API và trang chủ: Không cache để đảm bảo dữ liệu realtime.
        """
        if request.path.startswith('/static/'):
            if '/css/style.css' in request.path or '/js/main.js' in request.path:
                response.headers['Cache-Control'] = 'no-cache, must-revalidate'
            else:
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path.startswith('/api/') or request.path == '/':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    # ==================== CẤU HÌNH APSCHEDULER ====================
    # TƯ DUY KIẾN TRÚC: 
    # 1. Tránh lỗi chạy 2 lần khi bật Debug (Flask reloader).
    # 2. Đảm bảo Scheduler chỉ chạy trên một instance duy nhất (Tránh gửi trùng mail khi có nhiều Gunicorn worker).
    # - Biến RUN_SCHEDULER trong file .env kiểm soát việc này. Mặc định là 'true' cho Local.
    if os.environ.get('RUN_SCHEDULER', 'true').lower() == 'true':
        # Nếu đang ở chế độ Debug, chỉ chạy khi là tiến trình con (được reloader sinh ra)
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            apscheduler.init_app(app)
            
            # TƯ DUY QUAN TRỌNG: Phải import các hàm này bên trong create_app để tránh lỗi Circular Import.
            from app.scheduler import check_deadlines, check_budgets
            
            # Thêm các job vào Scheduler (Chạy định kỳ)
            # Ví dụ: Cứ mỗi 15 phút kiểm tra deadline 1 lần.
            apscheduler.add_job(id='check_deadlines_job', func=check_deadlines, trigger='interval', minutes=15)
            # Ví dụ: Cứ mỗi 30 phút kiểm tra ngân sách 1 lần.
            apscheduler.add_job(id='check_budgets_job', func=check_budgets, trigger='interval', minutes=30)
            
            apscheduler.start()
            app.logger.info("[Scheduler] APScheduler đã khởi động thành công.")

    return app


# Load user an toàn (tránh lỗi crash app nếu user_id không hợp lệ)
from app.models import User

@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)