import threading
import queue
import time
import uuid

# Tạo 2 hàng đợi (Queue) để giao tiếp
_input_queue = queue.Queue()
_output_queue = queue.Queue()
_worker_thread = None

def init_ai_worker():
    """Khởi tạo luồng AI (Chỉ gọi 1 lần)"""
    global _worker_thread
    
    if _worker_thread is not None and _worker_thread.is_alive():
        return

    from app.ai_worker import start_ai_worker
    
    # Sử dụng Thread thay vì Process
    _worker_thread = threading.Thread(
        target=start_ai_worker, 
        args=(_input_queue, _output_queue),
        daemon=True # Tự động tắt khi web tắt
    )
    _worker_thread.start()
    print("[AI Manager] Đã khởi tạo luồng AI thành công.")

def _send_task(task_data, timeout=10.0):
    """Hàm dùng chung để gửi task và chờ kết quả"""
    global _input_queue, _output_queue, _worker_thread
    
    if _worker_thread is None or not _worker_thread.is_alive():
        init_ai_worker()
        
    request_id = str(uuid.uuid4())
    task_data.append(request_id)
    
    try:
        _input_queue.put(tuple(task_data))
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                res_id, result = _output_queue.get(timeout=0.1)
                if res_id == request_id:
                    return result
            except queue.Empty:
                continue
        return None
    except Exception as e:
        print(f"[AI Manager] Lỗi giao tiếp: {e}")
        return None

def request_prediction(user_id, future_date, category, timeout=5.0):
    return _send_task(["PREDICT", user_id, future_date, category], timeout)

def request_training(user_id, timeout=30.0):
    return _send_task(["TRAIN", user_id], timeout)