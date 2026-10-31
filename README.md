# 🎯 Personal Planner: Hệ thống Quản lý Tài chính & Công việc

> **Đồ án thiết kế Hệ thống thông tin**  
> Được thiết kế và mở rộng thành ứng dụng Web quản lý tài chính cá nhân chuẩn Production, tích hợp kiến trúc **Tối ưu hóa hiệu năng đa tầng (Multi-tier Optimization)** và **Distributed Caching**.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-brightgreen)](https://personal-planner-kkac.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)](https://flask.palletsprojects.com/)
[![Turso](https://img.shields.io/badge/Turso-LibSQL-black)](https://turso.tech/)
[![Redis](https://img.shields.io/badge/Redis-Cloud%20Caching-red)](https://upstash.com/)
[![Tailwind](https://img.shields.io/badge/Tailwind-CSS-38B2AC)](https://tailwindcss.com/)

---

## 📑 THÔNG TIN DỰ ÁN & HƯỚNG DẪN ĐỐI CHIẾU

### 1. Nhận diện

- **Tên dự án:** Personal Planner - Hệ thống quản lý tài chính và công việc cá nhân.
- **Mục tiêu:** Giải quyết triệt để các bài toán về xử lý dữ liệu lớn, tối ưu hóa tài nguyên máy chủ (RAM/CPU) và mang lại trải nghiệm mượt mà như SPA.

### 2. Môi trường

- **Ngôn ngữ:** Python 3.10+
- **Thư viện sử dụng:** `Flask==2.3.3` (Web Server), `Flask-SQLAlchemy` (ORM), `Flask-Caching` & `redis` (Distributed Caching), `Flask-Compress` (Nén Gzip/Brotli), `APScheduler` (Cronjobs), `python-dotenv` (Quản lý biến môi trường).
- **Lệnh cài đặt:** `pip install -r requirements.txt`

### 3. Lệnh

- **Khởi tạo Database (Local):**
  `flask db upgrade`
- **Chạy Server Development:**
  `python run.py`
- **Chạy Production (Gunicorn):**
  `gunicorn -c gunicorn.conf.py run:app`
- **Build giao diện Tailwind CSS:**
  `python -m tailwindcss_bin -i ./app/static/css/input.css -o ./app/static/css/style.css --minify`

### 4. Quy ước

- **Input (Giao dịch):** Số tiền (VND), Ngày, Danh mục (7 loại), Ví (tùy chọn). Hệ thống tự động parse tiền tệ (VD: `10.000.000` -> `10000000`).
- **Input (Ngân sách):** Tháng, Năm, Danh mục, Số tiền. Hỗ trợ Upsert (Thêm mới hoặc Cập nhật).
- **Input (Công việc):** Tên, Mô tả, Hạn chót, Trạng thái, Tiến độ, **Mức độ Quan trọng (Ma trận)**.
- **Xử lý lỗi:** Validator của WTForms kiểm tra chặt chẽ, hiển thị thông báo lỗi màu đỏ nếu số tiền âm, sai định dạng ngày, hoặc vượt quá giới hạn.

### 5. Minh chứng

- **Giao diện:** Hỗ trợ Dark/Light mode, Skeleton Loading, biểu đồ Chart.js, phân loại công việc trực quan bằng Ma trận Eisenhower.
- **Hiệu năng:** Tốc độ phản hồi API Dashboard `< 200ms` nhờ Redis Cache.
- **Mã nguồn:** Được tổ chức theo mô hình App Factory, Blueprints rõ ràng.

---

## 📖 Giới thiệu

**Personal Planner** là một hệ sinh thái Full-stack được thiết kế để chạy cực nhẹ trên môi trường Cloud giới hạn (Render Free Tier - 512MB RAM). Điểm nhấn của dự án là việc ứng dụng **Thuật toán Thống kê (Statistical Forecasting)** và **Tối ưu hóa SQL (SQL Aggregation)** để thay thế cho các mô hình AI cồng kềnh.

Ứng dụng không chỉ dừng lại ở mức CRUD cơ bản mà giải quyết triệt để các bài toán về dự báo chi tiêu, phân bổ ngân sách thông minh, và quản lý công việc (tích hợp Ma trận Eisenhower), mang lại trải nghiệm mượt mà như ứng dụng Single Page Application (SPA).

---

## 🚀 Tính năng nổi bật

### 1. Kiến trúc Phân tán & Tối ưu hóa (System Architecture)

- **Turso (LibSQL) Database:** Sử dụng Turso Cloud Database cho Production, đảm bảo đồng bộ dữ liệu và chống mất mát khi server restart.
- **Upstash Redis Caching:** Lưu đệm API Dashboard, giảm 90% truy vấn DB. Tự động Fallback sang `SimpleCache` nếu mất kết nối Redis.
- **Nén Phản Hồi (Gzip/Brotli):** Tích hợp `Flask-Compress` giúp tiết kiệm 80% băng thông.
- **SQL Aggregation:** Sử dụng `func.sum()`, `group_by()` để DB tính toán, giảm tải RAM server.

### 2. Tối ưu hóa Thuật toán (Không dùng AI)

- **Weekday Moving Average:** Dự báo chi tiêu 7 ngày tới dựa trên thói quen chi tiêu theo từng thứ trong tuần.
- **Dynamic Budget Allocation:** Phân bổ ngân sách dựa trên Lịch sử chi tiêu + Trọng số ưu tiên.
- **Làm tròn 10k VNĐ:** Tự động làm tròn số tiền phân bổ và bù trừ sai số vào danh mục "Khác".
- **Ma trận Eisenhower (Eisenhower Matrix):** Tự động phân loại và sắp xếp công việc dựa trên 2 trục: **Quan trọng** (Cột mốc/Milestone) và **Khẩn cấp** (Hạn chót <= 3 ngày). Giao diện tự động gắn nhãn (Làm ngay, Lên lịch, Nhanh gọn, Bình thường) giúp người dùng tối ưu hóa thời gian.

### 3. Trực quan hóa & Trải nghiệm UI/UX

- **HTMX + View Transitions:** Chuyển trang mượt mà không cần SPA framework.
- **AJAX Slider:** Kéo thanh trượt tiến độ công việc, tự động tính toán lại trạng thái và lưu DB.
- **Skeleton Loading:** Hiệu ứng "Khung xương" trong lúc chờ API.
- **Import CSV thông minh:** Tự nhận diện bảng mã (UTF-8, CP1258), chống tràn RAM bằng Bulk Insert.
- **Custom Modal:** Thay thế `confirm()` mặc định bằng Modal thiết kế riêng.

---

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
| ------------ | ----------- |
| **Backend** | Python 3.10+, Flask 2.3.3, SQLAlchemy |
| **Caching** | Redis (Upstash Cloud), Flask-Caching |
| **Frontend** | Tailwind CSS v4, HTMX, Chart.js, Vanilla JS |
| **Database** | SQLite (Local), Turso LibSQL (Production) |
| **Scheduler** | APScheduler (Cronjobs gửi mail cảnh báo) |
| **Deployment** | Gunicorn (gthread), Render |

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
│   │   ├── transactions.py     # Quản lý Giao dịch (Import CSV)
│   │   └── wallet.py           # Quản lý Ví (Soft/Hard Delete)
│   ├── services/
│   │   └── financial_planner.py# Thuật toán chia ngân sách & làm tròn 10k
│   ├── static/
│   │   ├── css/                # Tailwind CSS (style.css, input.css)
│   │   └── js/                 # Mã JS (main.js - Event Delegation)
│   ├── templates/              # Jinja2 Templates (base.html, layouts)
│   ├── __init__.py             # App Factory & Extensions (DB, Cache)
│   ├── forms.py                # WTForms Validations
│   ├── models.py               # SQLAlchemy Models (User, Trans, Task)
│   └── scheduler.py            # Cronjobs gửi mail cảnh báo
├── migrations/                 # Thư mục quản lý DB Migration (Alembic)
├── .env                        # Biến môi trường (Không push lên Git)
├── config.py                   # Cấu hình môi trường (DB, Mail, Redis)
├── environment.yml             # Môi trường Conda (Local)
├── gunicorn.conf.py            # Cấu hình Production Server (gthread)
├── render.yaml                 # Cấu hình Deploy trên Render
├── requirements.txt            # Thư viện Python (Production)
└── run.py                      # Entry point khởi chạy Server
```

---

## ⚙️ Hướng dẫn cài đặt & Chạy

### Bước 1: Khởi tạo môi trường (Khuyên dùng Miniconda)

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

### Bước 3: Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc với nội dung:

```env
SECRET_KEY=chuoi-bi-mat-cua-ban
# Bỏ trống TURSO_DATABASE_URL và TURSO_AUTH_TOKEN để dùng SQLite Local
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=email-cua-ban@gmail.com
MAIL_PASSWORD=mat-khau-ung-dung-cua-ban
```

### Bước 4: Khởi tạo Database & Chạy chương trình

```bash
flask db upgrade
python run.py
```

Truy cập giao diện tại: **<http://127.0.0.1:5000>**

---

## 🌐 RESTful API

### 1. Lấy thông số Dashboard (Có Cache)

`GET /api/dashboard-stats?month=1&year=2024`

- Trả về thông tin Thu/Chi, Tài sản, Ngân sách, Dự báo chi tiêu 7 ngày tới, Insight.
- **Cập nhật:** Trả về danh sách Công việc sắp tới kèm theo trường `milestone` (Boolean) để Frontend render Ma trận Eisenhower.

### 2. Lập kế hoạch tài chính (Phân bổ ngân sách)

`POST /api/financial-plan`

- **Body:** JSON chứa thu nhập, tỷ lệ tiết kiệm, khu vực kinh tế.
- **Kết quả:** Phân bổ ngân sách đề xuất (đã bù trượt giá lạm phát) và số tiền tiết kiệm.

### 3. Cập nhật tiến độ công việc

`POST /tasks/update_progress/<id>`

- **Body:** JSON chứa `progress` (0-100). Tự động đổi trạng thái task sang `done` nếu 100%.

### 4. Import Giao dịch từ CSV

`POST /transactions/import`

- Hỗ trợ upload file, tự động nhận diện delimiter và encoding.

---

## ⚠️ Giới hạn & Lưu ý kỹ thuật

- **Render Free Tier (512MB RAM):** Render sẽ tự động "ngủ đông" (Spin down) nếu không có truy cập trong 15 phút. Sử dụng **UptimeRobot** để ping giữ web luôn "thức".
- **Lỗi build `libsql` trên Windows:** Gói `sqlalchemy-libsql` không hỗ trợ compile trên Windows. File `requirements.txt` đã cấu hình tự động bỏ qua gói này trên Windows.
- **Xử lý Timezone:** Lưu trữ UTC dưới DB, nhưng mọi tính toán trong Scheduler ép sang giờ Việt Nam (`Asia/Ho_Chi_Minh`) để tránh lệch 7 giờ.
- **Xử lý ngày tháng (Frontend):** Hàm parse ngày tháng trong JS đã được custom để đọc đúng định dạng `DD/MM/YYYY` (tránh lỗi `Invalid Date` của trình duyệt) khi tính toán Ma trận Eisenhower.

---

## 🚢 Triển khai Online (Live Demo)

👉 **<https://personal-planner-kkac.onrender.com/>**

---

## 📝 License

Dự án phục vụ mục đích học tập và phát triển cá nhân.
