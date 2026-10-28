import os
import queue
import time
from datetime import datetime

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def _extract_request_id(task):
    if isinstance(task, (tuple, list)) and len(task) >= 2:
        return task[-1]
    return None

def start_ai_worker(input_queue, output_queue):
    print("[AI Worker] Đã khởi động và đang chờ yêu cầu...")

    from app.ml.expense_model import predict_expense, train_model, _get_paths
    from app import create_app, db

    app = create_app()

    while True:
        try:
            task = input_queue.get(timeout=1)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[AI Worker] Queue error: {e}")
            continue

        if task == "STOP":
            print("[AI Worker] Nhận tín hiệu STOP, thoát.")
            break

        request_id = _extract_request_id(task)
        action = task[0] if isinstance(task, (tuple, list)) and task else None
        t0 = time.time()

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
                _, user_id, items, request_id = task
                print(f"[AI Worker] Đang xử lý PREDICT_BATCH cho {len(items)} items...")
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
                    
                    # ✅ TỰ PHỤC HỒI: Nếu dự đoán lỗi do file model hỏng, xóa đi để train lại
                    paths = _get_paths(user_id)
                    for p in paths.values():
                        if os.path.exists(p):
                            try:
                                os.remove(p)
                                print(f"[AI Worker] Đã xóa file lỗi {p} để chuẩn bị train lại.")
                            except:
                                pass

            else:
                print(f"[AI Worker] Hành động không hợp lệ: {action!r}")

        except Exception as e:
            print(f"[AI Worker] Lỗi xử lý '{action}' (request_id={request_id}): {e}")
            if request_id:
                try:
                    output_queue.put((request_id, None))
                except Exception:
                    pass
        finally:
            # ✅ QUAN TRỌNG: Đóng kết nối DB ngay sau khi xử lý xong để tránh rò rỉ
            try:
                with app.app_context():
                    db.session.remove()
            except Exception:
                pass

        elapsed_ms = int((time.time() - t0) * 1000)
        if elapsed_ms > 500: 
            print(f"[AI Worker] {action} mất {elapsed_ms}ms (request_id={request_id})")