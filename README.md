# 🎯 Personal Planner: AI-Powered Finance & Task Management

Hệ thống quản lý tài chính cá nhân và công việc tích hợp **Trí tuệ Nhân tạo (Machine Learning)**. Dự án không chỉ dừng lại ở mức CRUD cơ bản mà còn giải quyết các bài toán thực tế về tối ưu hóa ngân sách, dự báo chi tiêu và cập nhật dữ liệu thời gian thực.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![TensorFlow](https://img.shields.io/badge/AI-TensorFlow%2FKeras-orange.svg)](https://tensorflow.org/)
[![TailwindCSS](https://img.shields.io/badge/UI-Tailwind_CSS-38B2AC.svg)](https://tailwindcss.com/)

---

## 📖 Tổng quan

**Personal Planner** là một ứng dụng web Full-stack được thiết kế nhằm giúp người dùng kiểm soát dòng tiền và quản lý tiến độ công việc một cách thông minh. Điểm nhấn của dự án là việc tích hợp **Mạng Nơ-ron Nhân tạo (Neural Networks)** để phân tích lịch sử giao dịch và dự báo chi tiêu cho 7 ngày tiếp theo, kết hợp cùng **Thuật toán chia ngân sách tối ưu** dựa trên hành vi người dùng.

---

## 🔥 TRỌNG TÂM KỸ THUẬT (TECHNICAL HIGHLIGHTS)

### 1. Tích hợp Trí tuệ Nhân tạo (AI/ML Integration)

* **Custom Deep Neural Network:** Sử dụng TensorFlow/Keras xây dựng mạng nơ-ron (Dense Layers + Dropout) để dự đoán số tiền chi tiêu dựa trên 5 đặc trưng: Thứ trong tuần, Ngày, Tháng, Năm và Danh mục.
* **Kiến trúc Multi-tenant Model:** Hệ thống tự động tạo, huấn luyện và lưu trữ model **riêng biệt cho từng User** (`expense_model_{user_id}.h5`), tránh hiện tượng ghi đè dữ liệu giữa các tài khoản.
* **Bộ nhớ đệm (RAM Caching):** Model, Scaler và Encoder được lưu vào bộ nhớ đệm (Cache) sau lần load đầu tiên. Giúp API dự đoán phản hồi tức thì thay vì phải đọc file từ ổ cứng 21 lần mỗi khi load Dashboard.

### 2. Cập nhật Thời gian thực (Real-time Dashboard)

* **AJAX Polling:** Trang Tổng quan tự động gọi ngầm API mỗi 3 giây. Mọi thay đổi về Giao dịch hay Công việc ở tab khác sẽ lập tức được đồng bộ mà **không cần F5**.
* **Chống Cache trình duyệt:** Header `Cache-Control: no-store` được thiết lập ở Backend, kết hợp tham số `?t=timestamp` ở Frontend để đảm bảo dữ liệu luôn là mới nhất.
* **Biểu đồ Động (Chart.js):** Biểu đồ cột và biểu đồ đường tự động điều chỉnh màu sắc (Grid, Text, Tooltip) tương thích hoàn toàn với chế độ Sáng/Tối (Light/Dark Mode).

### 3. Thuật toán Lập kế hoạch Tài chính (Financial Planner Algorithm)

* **Dynamic Budget Allocation:** Tự động tính toán số tiền phân bổ cho từng danh mục (Ăn uống, Di chuyển, Khác) dựa trên: Thu nhập, Mục tiêu tiết kiệm, Lịch sử chi tiêu trung bình và Trọng số ưu tiên do người dùng chọn.
* **Xử lý lỗi SQLite (SQLite Pitfalls Avoidance):** Thay vì dùng hàm `SUM()` của Database (dễ sinh lỗi làm tròn với kiểu `Numeric`), hệ thống sử dụng Python để tính tổng trực tiếp, đảm bảo độ chính xác tuyệt đối cho dòng tiền.

### 4. Bảo mật & Kiến trúc Hệ thống

* **Bảo vệ CSRF (Cross-Site Request Forgery):** Tất cả các request AJAX (Cập nhật tiến độ, Lấy dữ liệu Dashboard) đều được đính kèm `X-CSRFToken` giải mã từ thẻ `<meta>`, ngăn chặn hoàn toàn các cuộc tấn công giả mạo.
* **Kiểu dữ liệu `Numeric(10,2)`:** Cột tiền tệ được định nghĩa chuẩn xác thay vì dùng `Float`, loại bỏ hoàn toàn lỗi `0.1 + 0.2 = 0.30000000000000004`.
* **Background Scheduler:** Sử dụng `APScheduler` chạy ngầm định kỳ, tự động quét và gửi Email cảnh báo khi Công việc sắp đến hạn hoặc Chi tiêu vượt quá Ngân sách.

---

## 🚀 CÁC TÍNH NĂNG CHÍNH

### 1. Quản lý Tài chính (Transactions & Budgets)

* **Giao dịch:** Thêm/Sửa/Xóa, phân loại Thu nhập/Chi tiêu, hỗ trợ Import hàng loạt qua file CSV.
* **Ngân sách:** Thiết lập hạn mức chi tiêu theo từng danh mục và tháng. Tự động cảnh báo khi vượt hạn mức.

### 2. Quản lý Công việc (Tasks)

* **Theo dõi tiến độ (AJAX Slider):** Kéo thanh trượt phần trăm, hệ thống tự động tính toán lại trạng thái (Chờ xử lý -> Đang làm -> Đã xong) và lưu vào Database ngay lập tức không cần load lại trang.
* **Cột mốc (Milestones):** Đánh dấu các công việc quan trọng bằng biểu tượng Ngôi sao.

### 3. Giao diện Người dùng (UI/UX)

* **Dark/Light Mode:** Chuyển đổi mượt mà, chống nháy sáng (FOUC) bằng Script chèn ở `<head>`.
* **Responsive:** Tương thích hoàn toàn trên Mobile và Tablet với Navbar dạng Hamburger Menu.
* **Custom Modal:** Thay thế hoàn toàn hộp thoại `confirm()` mặc định xấu xí của trình duyệt bằng Modal thiết kế riêng theo phong cách Tailwind.

---

## 🧠 THUẬT TOÁN & MÔ HÌNH AI

### 1. Mô hình Dự đoán Chi tiêu (Expense Prediction Model)

* **Input:** 5 features (`day_of_week`, `day_of_month`, `month`, `year`, `category_encoded`).
* **Data Preprocessing:** Sử dụng `StandardScaler` để chuẩn hóa dữ liệu và `LabelEncoder` để mã hóa danh mục.
* **Architecture:** `Dense(64, relu) -> Dropout(0.2) -> Dense(32, relu) -> Dense(1)`. Hàm loss: `MSE`, Optimizer: `Adam`.
* **Cơ chế Fallback:** Nếu User chưa có đủ 10 giao dịch chi tiêu, hệ thống sẽ trả về 0 và hiển thị thông báo "Chưa đủ dữ liệu" thay vì crash.

### 2. Thuật toán Chia ngân sách (Financial Planner)

* Công thức tính tỷ lệ phân bổ: `Tỷ lệ cơ sở = Chi tiêu danh mục / Tổng chi tiêu`.
* Tỷ lệ này được nhân với `Trọng số ưu tiên` (do người dùng nhập) và chuẩn hóa lại về 1.0. Số tiền còn lại sau khi trích lập quỹ tiết kiệm sẽ được nhân với tỷ lệ này.

---

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
| ------------ | ----------- |
| **Ngôn ngữ lõi** | Python 3.10+ |
| **Web Framework** | Flask 2.3.3 |
| **Database ORM** | Flask-SQLAlchemy (SQLite) |
| **AI & Machine Learning** | TensorFlow 2.15+, Keras, Scikit-learn, Pandas |
| **Form & Validation** | Flask-WTF, WTForms |
| **Giao diện** | Tailwind CSS, Chart.js |
| **Tiến trình chạy ngầm** | APScheduler, Flask-Mail |
| **Môi trường (Khuyên dùng)** | Miniconda (Windows) |

---

## 📂 Cấu trúc thư mục

```text
personal_planner/
├── app/
│   ├── ml/                     # Chứa logic AI
│   │   └── expense_model.py    # TensorFlow Model & Caching
│   ├── services/               # Business Logic
│   │   └── financial_planner.py# Thuật toán tính ngân sách
│   ├── routes/                 # Controllers
│   │   ├── api.py              # API Endpoints cho AJAX (Real-time)
│   │   ├── auth.py             # Đăng nhập/Đăng ký
│   │   ├── dashboard.py        # Trang Tổng quan
│   │   ├── transactions.py     # Giao dịch (Bao gồm Import CSV)
│   │   ├── budgets.py          # Ngân sách
│   │   └── tasks.py            # Công việc
│   ├── static/
│   │   ├── css/style.css       # Custom CSS (Dark Mode overrides)
│   │   ├── js/main.js          # AJAX, Modals, Sliders
│   │   └── models/             # Nơi lưu file .h5, .pkl của AI
│   ├── templates/              # Jinja2 Templates (Phân chia theo Module)
│   ├── __init__.py             # App Factory & Blueprint Registration
│   ├── forms.py                # WTForms Validations
│   ├── models.py               # SQLAlchemy Models
│   └── scheduler.py            # Cronjobs gửi mail cảnh báo
├── config.py                   # Cấu hình môi trường
├── run.py                      # Entry point
├── requirements.txt            # Thư viện Python
└── environment.yml             # File xuất môi trường Conda
```

---

## ⚙️ Hướng dẫn cài đặt & Chạy (Conda)

> ⚠️ **Lưu ý**: Dự án được tối ưu để chạy trên môi trường **Miniconda** (Khuyên dùng Python 3.10 để tương thích tốt nhất với TensorFlow trên Windows).

### Bước 1: Khởi tạo môi trường Conda

```bash
conda env create -f environment.yml
conda activate personal_planner
```

### Bước 2: Tạo Database (Migration)

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Bước 3: Cấu hình biến môi trường

Tạo file `.env` ở thư mục gốc và điền các thông tin sau (nếu muốn test tính năng gửi mail):

```env
SECRET_KEY=chuoi-bi-mat-cua-ban
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=email-cua-ban@gmail.com
MAIL_PASSWORD=mat-khau-ung-dung-cua-ban
```

### Bước 4: Khởi chạy Server

```bash
python run.py
```

Truy cập vào `http://127.0.0.1:5000` để trải nghiệm.

---

## ⚠️ Giới hạn & Lưu ý kỹ thuật

* **Yêu cầu dữ liệu cho AI:** Mô hình Dự đoán chi tiêu chỉ hoạt động khi tài khoản có **ít nhất 10 giao dịch chi tiêu**. Nếu chưa đủ, hệ thống sẽ hiển thị thông báo yêu cầu nhập thêm.
* **Múi giờ (Timezone):** Hệ thống sử dụng `datetime.now()` theo giờ máy chủ. Nếu deploy lên server nước ngoài, cần cấu hình lại Timezone để việc gửi mail nhắc nhở deadline được chính xác.
* **SQLite & Concurrent Writes:** Dự án dùng SQLite phù hợp cho đồ án môn học. Nếu phát triển thành sản phẩm thương mại, nên chuyển sang PostgreSQL để tránh lỗi khóa bảng (Table Lock) khi có nhiều người dùng truy cập cùng lúc.
