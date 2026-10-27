import multiprocessing

# Chỉ 1 worker để tiết kiệm RAM
workers = 1
# Sử dụng 4 luồng để xử lý request
threads = 4
worker_class = "gthread"
# Tăng timeout lên 120s vì model AI load lần đầu khá lâu
timeout = 120
# Không preload app để tránh nhân bản bộ nhớ
preload_app = False
bind = "0.0.0.0:10000"