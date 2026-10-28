# 🎯 Personal Planner: Performance-Optimized Finance & Task Manager

Ứng dụng quản lý tài chính cá nhân và công việc được thiết kế với kiến trúc **Tối ưu hóa hiệu năng đa tầng (Multi-tier Optimization)**. Dự án không chỉ dừng lại ở mức CRUD cơ bản mà giải quyết triệt để các bài toán về xử lý dữ liệu lớn, tối ưu hóa tài nguyên máy chủ (RAM/CPU) và mang lại trải nghiệm mượt mà như ứng dụng Single Page Application (SPA).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![TailwindCSS](https://img.shields.io/badge/UI-Tailwind_v4-38B2AC.svg)](https://tailwindcss.com/)
[![HTMX](https://img.shields.io/badge/Frontend-HTMX-3366CC.svg)](https://htmx.org/)
[![Turso](https://img.shields.io/badge/Database-Turso_LibSQL-black.svg)](https://turso.tech/)
[![Redis](https://img.shields.io/badge/Cache-Upstash_Redis-red.svg)](https://upstash.com/)

---

## 📖 Tổng quan

**Personal Planner** là một hệ sinh thái Full-stack được thiết kế để chạy cực nhẹ trên môi trường Cloud giới hạn (Render Free Tier - 512MB RAM). Điểm nhấn của dự án là việc ứng dụng **Thuật toán Thống kê (Statistical Forecasting)** và **Tối ưu hóa SQL (SQL Aggregation)** để thay thế cho các mô hình AI cồng kềnh. Nhờ đó, ứng dụng khởi động tức thì, phản hồi siêu tốc mà vẫn đảm bảo độ chính xác cao trong việc dự báo chi tiêu và phân bổ ngân sách.

---

## 🔥 TRỌNG TÂM KỸ THUẬT (TECHNICAL HIGHLIGHTS)

### 1. Tối ưu hóa Backend & Database

* **Turso (LibSQL) Database:** Sử dụng Turso Cloud Database cho môi trường Production, đảm bảo khả năng chịu tải, đồng bộ dữ liệu và không bị mất dữ liệu khi server khởi động lại.
* **Upstash Redis Caching:** Tích hợp bộ nhớ đệm phân tán cho API Dashboard, giảm tải truy vấn Database đi 90%. Tích hợp cơ chế Fallback tự động chuyển sang SimpleCache nếu mất kết nối Redis.
* **SQL Aggregation Triệt Để:** Loại bỏ hoàn toàn việc dùng vòng lặp Python để cộng trừ tiền. Sử dụng `func.sum()`, `group_by()` để Database tính toán, giảm tải RAM xuống mức gần như bằng 0.
* **Connection Pooling:** Cấu hình `pool_pre_ping` và `pool_recycle` giúp duy trì kết nối ổn định, chống đứt gãy (Broken Pipe) khi chạy trên Cloud.
* **Nén Phản Hồi (Gzip/Brotli):** Sử dụng `Flask-Compress` để nén toàn bộ dữ liệu (HTML, CSS, JSON) trước khi gửi về trình duyệt, tiết kiệm 80% băng thông.

### 2. Thuật toán Dự báo & Lập kế hoạch (Không dùng AI)

* **Weekday Moving Average:** Thuật toán dự báo chi tiêu 7 ngày tới dựa trên phân tích thói quen chi tiêu của người dùng theo từng thứ trong tuần (VD: Cuối tuần thường chi nhiều hơn).
* **Dynamic Budget Allocation:** Phân bổ ngân sách thông minh dựa trên Lịch sử chi tiêu + Trọng số ưu tiên do người dùng nhập.
* **Làm tròn tiền tệ (10k VNĐ):** Tự động làm tròn số tiền phân bổ đến hàng chục nghìn và bù trừ sai số vào danh mục "Khác", giúp bảng kế hoạch hiển thị đẹp mắt và thực tế.

### 3. Tối ưu hóa Frontend

* **HTMX:** Xử lý các tác vụ AJAX (như cập nhật thanh trượt tiến độ, xóa modal) không cần viết nhiều mã JavaScript.
* **Skeleton Loading:** Áp dụng hiệu ứng "Khung xương" (nhấp nháy) trong lúc chờ dữ liệu từ API, mang lại cảm giác mượt mà.
* **Tailwind CSS v4 Static Build:** Loại bỏ hoàn toàn CDN. Sử dụng Tailwind CLI để biên dịch ra file `style.css` tĩnh siêu nhẹ.
* **Async CSS & JS Defer:** Tối ưu hóa thứ tự tải tài nguyên, không chặn quá trình render giao diện.

---

## 🚀 CÁC TÍNH NĂNG CHÍNH

### 1. Quản lý Tài chính (Transactions & Budgets)

* **Giao dịch:** Thêm/Sửa/Xóa, phân loại 7 danh mục. Hỗ trợ Import hàng loạt qua file CSV (tự động nhận diện bảng mã UTF-8, CP1258 và chống tràn RAM bằng Bulk Insert).
* **Ngân sách:** Thiết lập hạn mức chi tiêu theo tháng. Cảnh báo khi vượt ngân sách.

### 2. Quản lý Công việc (Tasks)

* **Theo dõi tiến độ (AJAX Slider):** Kéo thanh trượt phần trăm, hệ thống tự động tính toán lại trạng thái và lưu vào Database ngay lập tức.
* **Cột mốc (Milestones):** Đánh dấu các công việc quan trọng.

### 3. Giao diện Người dùng (UI/UX)

* **Dark/Light Mode:** Chuyển đổi mượt mà, chống nháy sáng (FOUC).
* **Responsive:** Tương thích hoàn toàn trên Mobile và Tablet.
* **Custom Modal:** Thay thế hoàn toàn hộp thoại `confirm()` mặc định bằng Modal thiết kế riêng.

---

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
| ------------ | ----------- |
| **Ngôn ngữ lõi** | Python 3.10+ |
| **Web Framework** | Flask 2.3.3 |
| **Database** | SQLite (Local) / Turso LibSQL (Production) |
| **Caching & Nén** | Upstash Redis, Flask-Caching, Flask-Compress (Brotli/Gzip) |
| **Giao diện** | Tailwind CSS v4, Chart.js, HTMX |
| **Môi trường (Khuyên dùng)** | Miniconda (Windows) / Render (Linux) |

---

## 📂 Cấu trúc thư mục

```text
personal_planner/
├── app/
│   ├── routes/
│   │   ├── api.py              # API Endpoints (Dashboard, Financial Plan)
│   │   ├── auth.py             # Xác thực (Đăng nhập, Đăng ký, Quên MK)
│   │   ├── budgets.py          # Quản lý Ngân sách
│   │   ├── dashboard.py        # Trang Tổng quan
│   │   ├── tasks.py            # Quản lý Công việc
│   │   └── transactions.py     # Quản lý Giao dịch (Import CSV)
│   ├── services/
│   │   └── financial_planner.py# Thuật toán chia ngân sách & làm tròn 10k
│   ├── static/
│   │   ├── css/                # Tailwind CSS (style.css, input.css)
│   │   └── js/                 # Mã JS (main.js)
│   ├── templates/              # Jinja2 Templates (base.html, layouts)
│   ├── __init__.py             # App Factory & Extensions (DB, Cache)
│   ├── forms.py                # WTForms Validations
│   ├── models.py               # SQLAlchemy Models (User, Trans, Task)
│   └── scheduler.py            # Cronjobs gửi mail cảnh báo
├── migrations/                 # Thư mục quản lý DB Migration
├── .env                        # Biến môi trường (Không push lên Git)
├── config.py                   # Cấu hình môi trường (DB, Mail, Redis)
├── environment.yml             # Môi trường Conda (Local)
├── gunicorn.conf.py            # Cấu hình Production Server (gthread)
├── README.md                   # Tài liệu dự án
├── render.yaml                 # Cấu hình Deploy trên Render
├── requirements.txt            # Thư viện Python (Production)
└── run.py                      # Entry point khởi chạy Server
```

---

## ⚙️ Hướng dẫn cài đặt & Chạy (Local)

> ⚠️ **Lưu ý**: Dự án được tối ưu để chạy trên môi trường **Miniconda**. Yêu cầu cài đặt sẵn Python 3.10.

### Bước 1: Khởi tạo môi trường

```bash
conda env create -f environment.yml
conda activate personal_planner
pip install -r requirements.txt
```

### Bước 2: Build giao diện Tailwind CSS

```bash
# Cài đặt Tailwind CLI qua pip
pip install tailwindcss-bin

# Build file CSS tĩnh
python -m tailwindcss_bin -i ./app/static/css/input.css -o ./app/static/css/style.css --minify
```

### Bước 3: Khởi tạo Database (Local)

```bash
flask db upgrade
```

### Bước 4: Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc với các thông tin sau:

```env
SECRET_KEY=chuoi-bi-mat-cua-ban
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=email-cua-ban@gmail.com
MAIL_PASSWORD=mat-khau-ung-dung-cua-ban
```

### Bước 5: Khởi chạy Server

```bash
python run.py
```

Truy cập vào `http://127.0.0.1:5000` để trải nghiệm.

---

## ☁️ Triển khai lên Render (Production)

1. **Database:** Tạo database trên [Turso](https://turso.tech) (LibSQL). Lấy `TURSO_DATABASE_URL` và `TURSO_AUTH_TOKEN`.
2. **Cache:** Tạo database trên [Upstash](https://upstash.com) (Redis). Lấy `REDIS_URL`.
3. **Cấu hình Render Web Service:**
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `flask db upgrade && gunicorn -c gunicorn.conf.py run:app`
   * **Environment Variables:** Thêm các biến `FLASK_ENV=production`, `SECRET_KEY`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `REDIS_URL` và các biến `MAIL_*`.

---

## ⚠️ Giới hạn & Lưu ý kỹ thuật

* **Render Free Tier (512MB RAM):** Render sẽ tự động "ngủ đông" (Spin down) nếu không có truy cập trong 15 phút. Điều này khiến Scheduler (gửi mail) tạm dừng. Để khắc phục, hãy sử dụng dịch vụ ping định kỳ như **UptimeRobot** (ping mỗi 10-14 phút) để giữ web luôn "thức".
* **SQLite vs Turso:** Khi chạy Local, SQLite phù hợp cho mục đích phát triển. Trên Production (Render), hệ thống đã được cấu hình tự động chuyển sang Turso (LibSQL) để đảm bảo khả năng chịu tải và không bị mất dữ liệu khi khởi động lại.
* **Lỗi build `libsql` trên Windows:** Gói `sqlalchemy-libsql` không hỗ trợ compile trên Windows. File `requirements.txt` đã được cấu hình để tự động bỏ qua gói này khi chạy Local, chỉ cài đặt trên môi trường Linux (Render).
