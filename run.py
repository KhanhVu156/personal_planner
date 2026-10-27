import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

from app import create_app
from app.services.ai_manager import init_ai_worker
import multiprocessing

app = create_app()

# CHỈ khởi tạo AI Worker nếu đây là tiến trình chính (Main Process)
# Điều này ngăn chặn lỗi spawn vô hạn trên Windows
if multiprocessing.current_process().name == 'MainProcess':
    init_ai_worker()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host=host, port=port)