from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Numeric, CheckConstraint
from app import db


def utc_now():
    """
    Trả về thời gian hiện tại theo chuẩn UTC (Naive datetime - không chứa timezone).
    
    TƯ DUY THIẾT KẾ (Time Zone Best Practice):
    - Mọi thời gian (created_at, updated_at) lưu vào Database BẮT BUỘC phải là UTC.
    - Lý do: Server có thể chạy ở bất kỳ múi giờ nào, nhưng UTC là "ngôn ngữ chung" toàn cầu.
    - Khi hiển thị cho người dùng (ở VN), tầng View/API sẽ tự động cộng thêm 7 tiếng.
    - Tránh dùng `datetime.utcnow()` vì hàm này đã bị deprecated ở Python 3.12+.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    """Bảng lưu trữ thông tin người dùng."""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # TƯ DUY: cascade="all, delete-orphan" đảm bảo khi User bị xóa, 
    # toàn bộ Giao dịch, Ngân sách, Công việc của user đó cũng bị xóa theo (tránh rác DB).
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Băm mật khẩu bằng thuật toán bảo mật của Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Kiểm tra mật khẩu người dùng nhập với mã Hash trong DB."""
        return check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    """Bảng lưu trữ Giao dịch (Thu nhập / Chi tiêu)."""
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # TƯ DUY: Cột date lưu kiểu Date (chỉ có ngày/tháng/năm). 
    # User nhập ngày nào thì lưu ngày đó, không phụ thuộc vào giờ server.
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date(), index=True)
    
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(Numeric(30, 2), nullable=False) # Dùng Numeric để tránh lỗi làm tròn của Float
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        # Ràng buộc dữ liệu (Data Integrity) ở tầng Database
        CheckConstraint("type IN ('income', 'expense')", name='ck_trans_type'),
        CheckConstraint("amount > 0", name='ck_trans_amount_positive'),
        # Tối ưu hóa Index cho các query thống kê
        db.Index('ix_trans_user_date', 'user_id', 'date'),
        db.Index('ix_trans_user_type_date', 'user_id', 'type', 'date'),
        db.Index('ix_trans_user_category_date', 'user_id', 'category', 'date'),
    )


class Budget(db.Model):
    """Bảng lưu trữ Ngân sách theo tháng."""
    __tablename__ = 'budget'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    month = db.Column(db.Integer, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    amount = db.Column(Numeric(30, 2), nullable=False)

    __table_args__ = (
        CheckConstraint('month >= 1 AND month <= 12', name='ck_budget_month'),
        CheckConstraint('amount > 0', name='ck_budget_amount_positive'),
        # Chặn việc 1 user có 2 ngân sách trùng danh mục trong cùng 1 tháng/năm
        db.UniqueConstraint('user_id', 'category', 'month', 'year', name='uq_budget_user_cat_ym'),
        db.Index('ix_budget_user_ym', 'user_id', 'month', 'year'),
    )


class Task(db.Model):
    """Bảng lưu trữ Công việc (Tasks)."""
    __tablename__ = 'task'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # TƯ DUY: deadline lưu DateTime (Ngày + Giờ). 
    # Giờ này do User nhập, được hiểu là giờ VN. Scheduler sẽ xử lý để so sánh đúng.
    deadline = db.Column(db.DateTime, nullable=False, index=True)
    
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    milestone = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'done')", name='ck_task_status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_task_progress'),
        db.Index('ix_task_user_status_deadline', 'user_id', 'status', 'deadline'),
    )