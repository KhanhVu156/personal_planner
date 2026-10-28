import os

workers = 1
threads = 8
worker_class = "gevent"
worker_connections = 1000
timeout = 120
preload_app = False

# TỰ ĐỘNG ĐỌC CỔNG TỪ RENDER
port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"