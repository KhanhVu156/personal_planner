import os

workers = 1
threads = 8 # Xử lý 8 luồng (I/O bound + AI Worker chạy ngầm)
worker_class = "gthread" # Gthread an toàn với TensorFlow và SQLAlchemy
timeout = 120
preload_app = False

port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"