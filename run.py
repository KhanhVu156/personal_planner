import os
from app import create_app

# ============================================================
# TƯ DUY THIẾT KẾ (App Factory Pattern):
# - Khởi tạo Flask App thông qua hàm create_app() thay vì khởi tạo trực tiếp.
# - Giúp dễ dàng viết Unit Test, quản lý cấu hình linh hoạt theo môi trường.
# ============================================================
app = create_app()

if __name__ == '__main__':
    # --------------------------------------------------------
    # CẤU HÌNH MÔI TRƯỜNG (12-Factor App)
    # Đọc các biến môi trường để linh hoạt chuyển đổi giữa Dev / Prod.
    # --------------------------------------------------------
    
    # 1. Debug Mode: Mặc định TẮT để an toàn (tránh lộ thông tin trên Prod).
    # Chỉ bật khi set biến môi trường FLASK_DEBUG=True.
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 2. Host: Mặc định 0.0.0.0 để có thể truy cập từ mạng LAN / Docker.
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    
    # 3. Port: Có xử lý lỗi an toàn nếu biến môi trường bị set sai.
    # (Ví dụ: PORT="abc" sẽ không làm crash app mà tự fallback về 5000).
    try:
        port = int(os.environ.get('PORT', 5000))
    except (ValueError, TypeError):
        port = 5000

    # --------------------------------------------------------
    # KHỞI CHẠY SERVER
    # Lưu ý: app.run() chỉ dùng cho môi trường Development / Local.
    # Khi lên Production (thực tế), nên dùng WSGI Server chuyên dụng
    # như Gunicorn (Linux) hoặc Waitress (Windows) để đảm bảo hiệu năng.
    # --------------------------------------------------------
    app.run(
        debug=debug_mode, 
        host=host, 
        port=port,
        threaded=True # Đảm bảo xử lý đa luồng (tránh block khi request chậm)
    )