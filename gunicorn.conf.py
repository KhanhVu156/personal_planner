import os

workers = 1
threads = 8 # Dùng 8 luồng để xử lý request
worker_class = "gthread" # ĐỔI TỪ GEVENT VỀ GTHREAD
timeout = 120
preload_app = False

port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"