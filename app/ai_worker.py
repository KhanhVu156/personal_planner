import time
import os
from datetime import datetime

# Tắt cảnh báo rác
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

def start_ai_worker(input_queue, output_queue):
    """
    Hàm này chạy trong một tiến trình (process) riêng biệt.
    Nó lắng nghe input_queue, xử lý AI và trả kết quả vào output_queue.
    """
    print("[AI Worker] Đã khởi động và đang chờ yêu cầu...")
    
    # Import muộn để tiến trình này chỉ tốn RAM khi thực sự gọi AI
    from app.ml.expense_model import predict_expense, train_model
    from app import create_app, db
    
    # Tạo một app context ảo cho tiến trình con để có thể query Database
    app = create_app()
    
    while True:
        try:
            # Lấy yêu cầu từ hàng đợi (chờ tối đa 1 giây)
            task = input_queue.get(timeout=1)
            
            # Nếu nhận được tín hiệu dừng thì thoát
            if task == "STOP":
                break
                
            action = task[0]
            
            if action == "PREDICT":
                _, user_id, future_date, category, request_id = task
                with app.app_context():
                    result = predict_expense(user_id, future_date, category, db.session)
                    if result is None:
                        result = 0.0
                output_queue.put((request_id, result))
                
            elif action == "TRAIN":
                _, user_id, request_id = task
                with app.app_context():
                    result = train_model(user_id, db.session)
                    success = True if result is not None else False
                output_queue.put((request_id, success))
                
        except Exception as e:
            if "Empty" not in str(type(e)): # Bỏ qua lỗi timeout rỗng của Queue
                print(f"[AI Worker] Lỗi: {e}")
            continue