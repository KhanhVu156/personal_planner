import queue
import threading
import uuid
from concurrent.futures import Future, TimeoutError

_input_queue = queue.Queue()
_output_queue = queue.Queue()

_worker_thread = None
_dispatcher_thread = None
_init_lock = threading.Lock()

_pending: dict[str, Future] = {}
_pending_lock = threading.Lock()

_STOP = "STOP"

def _ensure_worker():
    global _worker_thread
    with _init_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return
        from app.ai_worker import start_ai_worker
        _worker_thread = threading.Thread(
            target=start_ai_worker,
            args=(_input_queue, _output_queue),
            daemon=True,
            name='ai-worker',
        )
        _worker_thread.start()
        print("[AI Manager] Đã khởi tạo luồng AI thành công.")

def _dispatch_loop():
    while True:
        try:
            item = _output_queue.get()
        except Exception:
            continue
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            continue
        res_id, result = item
        with _pending_lock:
            fut = _pending.pop(res_id, None)
        if fut is not None and not fut.done():
            try:
                fut.set_result(result)
            except Exception:
                pass

def _ensure_dispatcher():
    global _dispatcher_thread
    with _init_lock:
        if _dispatcher_thread is not None and _dispatcher_thread.is_alive():
            return
        _dispatcher_thread = threading.Thread(
            target=_dispatch_loop,
            daemon=True,
            name='ai-dispatcher',
        )
        _dispatcher_thread.start()

def _send_task(task_data, timeout=10.0):
    _ensure_worker()
    _ensure_dispatcher()

    request_id = str(uuid.uuid4())
    fut = Future()
    with _pending_lock:
        _pending[request_id] = fut

    try:
        _input_queue.put(tuple(task_data) + (request_id,), timeout=2.0)
        return fut.result(timeout=timeout)
    except TimeoutError:
        print(f"[AI Manager] LỖI TIMEOUT: Tác vụ {task_data[0]} quá {timeout}s. (Có thể AI đang train)")
        with _pending_lock:
            _pending.pop(request_id, None)
        return None
    except Exception as e:
        print(f"[AI Manager] Lỗi gửi task: {e}")
        with _pending_lock:
            _pending.pop(request_id, None)
        return None

def init_ai_worker():
    _ensure_worker()
    _ensure_dispatcher()

def request_prediction(user_id, future_date, category, timeout=5.0):
    return _send_task(["PREDICT", user_id, future_date, category], timeout=timeout)

def request_training(user_id, timeout=60.0):
    return _send_task(["TRAIN", user_id], timeout=timeout)

def request_prediction_batch(user_id, items, timeout=60.0):
    return _send_task(["PREDICT_BATCH", user_id, list(items)], timeout=timeout)

def shutdown_ai_worker():
    try:
        _input_queue.put(_STOP, timeout=1.0)
    except Exception:
        pass