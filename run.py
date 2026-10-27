from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Mặc định tắt Debug để an toàn khi đưa lên môi trường thực tế (Production)
    # Khi code ở máy cá nhân, ông chỉ cần thêm FLASK_DEBUG=True vào file .env là được
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Mặc định dùng '0.0.0.0' để có thể truy cập từ điện thoại (cùng mạng Wifi)
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug, host=host, port=port)