import os
import queue
import time
from datetime import datetime

# Tắt cảnh báo rác
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


def _extract_request_id(task):
    """
    Trả về request_id (phần tử cuối) nếu task là tuple/list có ≥2 phần tử,
    ngược lại trả None. Dùng để caller không bị treo timeout khi task malformed.
    """
    if isinstance(task, (tuple, list)) and len(task) >= 2:
        return task[-1]
    return None


def start_ai_worker(input_queue, output_queue):
    """
    Chạy trong background thread (xem app/services/ai_manager.py).

    ⚠️ LƯU Ý: ai_manager.py hiện dùng `threading.Thread` → `queue.Queue`
    (thread-safe) là đúng. Nếu sau này chuyển sang `multiprocessing.Process`,
    PHẢI đổi ai_manager sang `multiprocessing.Queue` (và giữ nguyên import
    `import queue` cho `queue.Empty`).

    Protocol message:
        input : (action, *args, request_id)
        output: (request_id, result)
        STOP  : input chỉ cần gửi string "STOP"
    """
    print("[AI Worker] Đã khởi động và đang chờ yêu cầu...")

    # Import muộn để chỉ tốn RAM khi thực sự xử lý AI
    from app.ml.expense_model import predict_expense, train_model
    from app import create_app, db

    # App context riêng cho worker
    app = create_app()

    while True:
        # ---------- Lấy task ----------
        try:
            task = input_queue.get(timeout=1)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[AI Worker] Queue error: {e}")
            continue

        # ---------- Tín hiệu dừng ----------
        if task == "STOP":
            print("[AI Worker] Nhận tín hiệu STOP, thoát.")
            break

        # ✅ Lấy request_id TRƯỚC khi unpack để nếu unpack fail vẫn báo được caller
        request_id = _extract_request_id(task)
        action = task[0] if isinstance(task, (tuple, list)) and task else None
        t0 = time.time()

        # ---------- Xử lý task ----------
        try:
            if action == "PREDICT":
                _, user_id, future_date, category, request_id = task
                with app.app_context():
                    result = predict_expense(user_id, future_date, category, db.session)
                output_queue.put((request_id, 0.0 if result is None else float(result)))

            elif action == "TRAIN":
                _, user_id, request_id = task
                with app.app_context():
                    result = train_model(user_id, db.session)
                output_queue.put((request_id, result is not None))

            elif action == "PREDICT_BATCH":
                # ✅ FIX P0: indentation đúng — cùng cấp với các elif phía trên
                _, user_id, items, request_id = task
                try:
                    with app.app_context():
                        results = []
                        for future_date, category in items:
                            r = predict_expense(user_id, future_date, category, db.session)
                            results.append(0.0 if r is None else float(r))
                    output_queue.put((request_id, results))
                except Exception as e:
                    print(f"[AI Worker] PREDICT_BATCH lỗi bên trong: {e}")
                    output_queue.put((request_id, [0.0] * len(items)))

            else:
                print(f"[AI Worker] Hành động không hợp lệ: {action!r}")

        except Exception as e:
            # Không nuốt lỗi — vẫn put None để caller được giải phóng.
            # request_id đã lấy được từ _extract_request_id nếu task đúng format.
            print(
                f"[AI Worker] Lỗi xử lý '{action}' "
                f"(request_id={request_id}): {e}"
            )
            if request_id:
                try:
                    output_queue.put((request_id, None))
                except Exception:
                    pass

        else:
            # Log thời gian (chỉ khi thành công) để tiện debug performance
            elapsed_ms = int((time.time() - t0) * 1000)
            if elapsed_ms > 500:  # chỉ log khi chậm (> 500ms)
                print(f"[AI Worker] {action} mất {elapsed_ms}ms (request_id={request_id})")