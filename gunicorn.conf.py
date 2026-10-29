import os

# TƯ DUY TỐI ƯU (Render Free Tier):
# - Render Free cung cấp 512MB RAM. 
# - Chạy 1 worker với 8 threads (gthread) là điểm cân bằng hoàn hảo cho các app Flask I/O Bound (chờ DB, chờ gửi mail).
# - Nếu chạy nhiều worker, RAM sẽ bị chia nhỏ và dễ bị Crash (OOM - Out Of Memory).
workers = 1
threads = 8
worker_class = "gthread" 

timeout = 120
preload_app = False

port = int(os.environ.get("PORT", 10000))
bind = f"0.0.0.0:{port}"

# TƯ DUY LOGGING: Ghi log ra stdout/stderr để Render có thể bắt được và hiển thị trên Dashboard.
accesslog = "-"
errorlog = "-"
loglevel = "info"