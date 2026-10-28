# 🎯 Personal Planner: AI-Powered & Performance-Optimized Finance Manager

Ứng dụng quản lý tài chính cá nhân và công việc tích hợp **Trí tuệ Nhân tạo (AI)** cùng kiến trúc **Tối ưu hóa hiệu năng đa tầng (Multi-tier Optimization)**. Dự án không chỉ dừng lại ở mức CRUD cơ bản mà giải quyết triệt để các bài toán về dự báo chi tiêu, tối ưu hóa tài nguyên máy chủ (RAM/CPU) và mang lại trải nghiệm người dùng mượt mà như ứng dụng Single Page Application (SPA).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![TensorFlow Lite](https://img.shields.io/badge/AI-TFLite%20%2B%20Distillation-orange.svg)](https://tensorflow.org/lite)
[![TailwindCSS](https://img.shields.io/badge/UI-Tailwind_v4-38B2AC.svg)](https://tailwindcss.com/)
[![HTMX](https://img.shields.io/badge/Frontend-HTMX-3366CC.svg)](https://htmx.org/)

---

## 📖 Tổng quan

**Personal Planner** là một hệ sinh thái Full-stack được thiết kế để chạy cực nhẹ trên môi trường Cloud giới hạn (Render Free Tier - 512MB RAM). Điểm nhấn của dự án là việc áp dụng **Knowledge Distillation (Chưng cất tri thức)** để tạo ra một mô hình AI siêu nhỏ (TFLite) nhưng vẫn đảm bảo độ chính xác, kết hợp cùng kiến trúc **đa tiến trình (Multiprocessing)** giúp tách biệt hoàn toàn gánh nặng AI ra khỏi luồng xử lý web chính.

---

## 🔥 TRỌNG TÂM KỸ THUẬT (TECHNICAL HIGHLIGHTS)

### 1. Tối ưu hóa Trí tuệ Nhân tạo (AI Level 4)

* **Knowledge Distillation (Teacher-Student):** Huấn luyện một mô hình "Giáo viên" phức tạp (64-32-16 neurons) để dạy lại kiến thức cho một mô hình "Học trò" siêu nhẹ (16-8 neurons). Kết quả: Mô hình nhỏ hơn 4 lần nhưng độ chính xác gần như tương đương.
* **TensorFlow Lite (TFLite):** Sử dụng kỹ thuật Quantization (Lượng tử hóa) để nén mô hình từ 32-bit float xuống 8-bit integer. File lưu ra (`.tflite`) cực nhẹ, suy luận (inference) cực nhanh trên CPU.
* **Kiến trúc Async Worker:** Tách biệt tiến trình AI (chạy ngầm) ra khỏi tiến trình Web chính (Flask) thông qua `multiprocessing`. Nếu AI bị crash do hết RAM, web chính vẫn hoạt động bình thường.

### 2. Tối ưu hóa Backend & Database (Level 1 & 3)

* **SQL Aggregation Triệt Để:** Loại bỏ hoàn toàn việc dùng vòng lặp Python để cộng trừ tiền. Sử dụng `func.sum()`, `group_by()` để Database tính toán, giảm tải RAM xuống mức gần như bằng 0.
* **Upstash Redis Caching:** Tích hợp bộ nhớ đệm phân tán (Redis) cho API Dashboard, giảm tải truy vấn Database đi 90%. Tích hợp cơ chế Fallback (tự động chuyển sang SimpleCache nếu Redis lỗi).
* **Connection Pooling:** Cấu hình `pool_pre_ping` và `pool_recycle` giúp duy trì kết nối ổn định, chống đứt gãy khi chạy trên Cloud.
* **Nén Phản Hồi (Gzip/Brotli):** Sử dụng `Flask-Compress` để nén toàn bộ dữ liệu (HTML, CSS, JSON) trước khi gửi về trình duyệt, tiết kiệm 80% băng thông.

### 3. Tối ưu hóa Frontend (Level 2 & 4)

* **HTMX (SPA Navigation):** Thay thế cơ chế tải lại trang truyền thống. Mọi thao tác click link được xử lý ngầm qua AJAX, chỉ thay thế phần thân (body) giúp việc chuyển trang diễn ra tức thì, không bị chớp trắng (FOUC).
* **Skeleton Loading:** Áp dụng hiệu ứng "Khung xương" (nhấp nháy) trong lúc chờ dữ liệu từ API, mang lại cảm giác mượt mà và chuyên nghiệp.
* **Tailwind CSS v4 Static Build:** Loại bỏ hoàn toàn CDN (nặng hàng trăm KB). Sử dụng Tailwind CLI để biên dịch ra file `style.css` tĩnh chỉ chứa các class thực tế được dùng (siêu nhẹ ~15KB).
* **Async CSS & JS Defer:** Tối ưu hóa thứ tự tải tài nguyên, không chặn quá trình render giao diện.

### 4. Thuật toán Lập kế hoạch Tài chính (Financial Algorithm)

* **Dynamic Budget Allocation:** Phân bổ ngân sách thông minh dựa trên Lịch sử chi tiêu + Trọng số ưu tiên do người dùng nhập.
* **Làm tròn tiền tệ (10k VNĐ):** Tự động làm tròn số tiền phân bổ đến hàng chục nghìn và bù trừ sai số vào danh mục "Khác", giúp bảng kế hoạch hiển thị đẹp mắt như các app ngân hàng thực thụ.

---

## 🚀 CÁC TÍNH NĂNG CHÍNH

### 1. Quản lý Tài chính (Transactions & Budgets)

* **Giao dịch:** Thêm/Sửa/Xóa, phân loại 7 danh mục (Ăn uống, Di chuyển, Học tập, Giải trí, Mua sắm, Hóa đơn, Khác). Hỗ trợ Import hàng loạt qua file CSV (sử dụng Generator để tránh tràn RAM).
* **Ngân sách:** Thiết lập hạn mức chi tiêu theo tháng.

### 2. Quản lý Công việc (Tasks)

* **Theo dõi tiến độ (AJAX Slider):** Kéo thanh trượt phần trăm, hệ thống tự động tính toán lại trạng thái và lưu vào Database ngay lập tức.
* **Cột mốc (Milestones):** Đánh dấu các công việc quan trọng bằng biểu tượng Ngôi sao.

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
| **AI & Machine Learning** | TensorFlow-CPU, Keras, TFLite, Scikit-learn |
| **Caching & Nén** | Upstash Redis, Flask-Caching, Flask-Compress (Brotli/Gzip) |
| **Giao diện** | Tailwind CSS v4, Chart.js, HTMX |
| **Môi trường (Khuyên dùng)** | Miniconda (Windows) / Render (Linux) |

---

## 📂 Cấu trúc thư mục

personal_planner/
├── app/
│   ├── ai_worker.py            # Tiến trình chạy AI độc lập (Multiprocessing)
│   ├── ml/
│   │   └── expense_model.py    # TFLite Model & Knowledge Distillation
│   ├── services/
│   │   ├── ai_manager.py       # Cầu nối giao tiếp giữa Flask và AI Worker
│   │   └── financial_planner.py# Thuật toán chia ngân sách & làm tròn 10k
│   ├── routes/                 # Controllers (API, Auth, Dashboard, ...)
│   ├── static/                 # Chứa file build tĩnh (style.css, dashboard.js)
│   ├── templates/              # Jinja2 Templates (Hỗ trợ HTMX)
│   ├── **init**.py             # App Factory & Cấu hình nén, cache, db
│   ├── forms.py                # WTForms Validations
│   ├── models.py               # SQLAlchemy Models (Numeric type)
│   └── scheduler.py            # Cronjobs gửi mail cảnh báo
├── config.py                   # Cấu hình môi trường (DB, Mail, Redis)
├── gunicorn.conf.py            # Cấu hình Production Server (gthread)
├── Procfile                    # Lệnh khởi chạy cho Render
├── run.py                      # Entry point
├── requirements.txt            # Thư viện Python
└── tailwind.config.js          # Cấu hình build Tailwind v4

---

## ⚙️ Hướng dẫn cài đặt & Chạy (Local)

> ⚠️ **Lưu ý**: Dự án được tối ưu để chạy trên môi trường **Miniconda**. Yêu cầu cài đặt sẵn Python 3.10 để tương thích với TensorFlow.

### Bước 1: Khởi tạo môi trường

conda env create -f environment.yml
conda activate personal_planner
pip install -r requirements.txt

### Bước 2: Build giao diện Tailwind CSS

# Cài đặt Tailwind CLI qua pip

pip install tailwindcss-bin

# Build file CSS tĩnh

python -m tailwindcss_bin -i ./app/static/css/input.css -o ./app/static/css/style.css --minify

### Bước 3: Khởi tạo Database (Local)

flask db upgrade

### Bước 4: Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc với các thông tin sau (để test gửi mail):
SECRET_KEY=chuoi-bi-mat-cua-ban
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=<email-cua-ban@gmail.com>
MAIL_PASSWORD=mat-khau-ung-dung-cua-ban

### Bước 5: Khởi chạy Server

python run.py
Truy cập vào `http://127.0.0.1:5000` để trải nghiệm.

---

## ☁️ Triển khai lên Render (Production)

1. **Database:** Tạo database trên [Turso](https://turso.tech) (LibSQL). Lấy `TURSO_DATABASE_URL` và `TURSO_AUTH_TOKEN`.
2. **Cache:** Tạo database trên [Upstash](https://upstash.com) (Redis). Lấy `REDIS_URL`.
3. **Cấu hình Render Web Service:**
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `flask db upgrade && gunicorn -c gunicorn.conf.py run:app`
   * **Environment Variables:** Thêm các biến `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `REDIS_URL` và các biến `MAIL_*`.

---

## ⚠️ Giới hạn & Lưu ý kỹ thuật

* **Yêu cầu dữ liệu cho AI:** Mô hình Dự đoán chi tiêu chỉ hoạt động khi tài khoản có **ít nhất 10 giao dịch chi tiêu**.
* **Render Free Tier (512MB RAM):** Mặc dù đã tách tiến trình AI, nhưng nếu có quá nhiều người dùng truy cập cùng lúc, Render có thể tự động khởi động lại (Spin down/up). Để giữ web luôn "thức", nên sử dụng dịch vụ ping định kỳ như UptimeRobot.
* **SQLite & Concurrent Writes:** Khi chạy Local, SQLite phù hợp cho mục đích phát triển. Trên Production (Render), hệ thống đã được cấu hình tự động chuyển sang Turso (LibSQL) để đảm bảo khả năng chịu tải và không bị mất dữ liệu khi khởi động lại.
