import os
from app import create_app

# Khởi tạo Flask App thông qua App Factory Pattern
app = create_app()

if __name__ == '__main__':
    # Lấy cấu hình từ biến môi trường, mặc định chạy ở port 5000 khi dev
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Chạy server phục vụ phát triển (Không dùng cho Production)
    app.run(debug=debug, host=host, port=port)