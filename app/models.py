from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Numeric, CheckConstraint
from app import db


def utc_now():
    """
    Trả về thời gian hiện tại theo chuẩn UTC (Naive datetime - không chứa timezone).
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

    # Mối quan hệ: Xóa user -> Xóa toàn bộ Ví, Giao dịch, Ngân sách, Công việc
    wallets = db.relationship('Wallet', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Wallet(db.Model):
    """
    Bảng quản lý Đa Ví (Nguồn tiền).
    Ví dụ: Tiền mặt, VietinBank, Momo, Thẻ tín dụng...
    """
    __tablename__ = 'wallet'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)
    wallet_type = db.Column(db.String(20), nullable=False, default='cash') # cash, bank, ewallet, credit
    
    # Số dư ban đầu rất quan trọng khi user tạo ví mới.
    initial_balance = db.Column(Numeric(30, 2), nullable=False, default=0)
    
    # Không bao giờ xóa cứng ví (tránh mất lịch sử). Chỉ ẩn đi (is_active=False).
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        # Một user không thể có 2 ví cùng tên (VD: 2 ví "Tiền mặt")
        db.UniqueConstraint('user_id', 'name', name='uq_wallet_user_name'),
        # Ràng buộc loại ví hợp lệ
        CheckConstraint("wallet_type IN ('cash', 'bank', 'ewallet', 'credit')", name='ck_wallet_type'),
    )


class Transaction(db.Model):
    """Bảng lưu trữ Giao dịch (Thu nhập / Chi tiêu)."""
    __tablename__ = 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Thêm wallet_id để liên kết giao dịch với Ví.
    # Cho phép NULL để tương thích ngược với dữ liệu cũ.
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.id', ondelete='RESTRICT'), nullable=True, index=True)
    
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date(), index=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(Numeric(30, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # FIX QUAN TRONG: Khai báo relationship để Transaction có thể truy cập thuộc tính .wallet
    wallet = db.relationship('Wallet', backref=db.backref('transactions', lazy='dynamic'))

    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name='ck_trans_type'),
        CheckConstraint("amount > 0", name='ck_trans_amount_positive'),
        db.Index('ix_trans_user_wallet_date', 'user_id', 'wallet_id', 'date'),
        db.Index('ix_trans_user_date', 'user_id', 'date'),
        db.Index('ix_trans_user_type_date', 'user_id', 'type', 'date'),
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
    
    # TƯ DUY MA TRẬN EISENHOWER (Trục Khẩn cấp): 
    # Trường deadline kết hợp với ngày hiện tại sẽ được dùng để tính toán xem công việc có khẩn cấp hay không (VD: <= 3 ngày).
    deadline = db.Column(db.DateTime, nullable=False, index=True)
    
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    progress = db.Column(db.Integer, default=0, nullable=False)
    
    # TƯ DUY MA TRẬN EISENHOWER (Trục Quan trọng): 
    # Trường milestone (Cột mốc) đại diện cho trục "Quan trọng" trong Ma trận. 
    # milestone = True -> Quan trọng (Đóng góp vào mục tiêu lớn).
    # milestone = False -> Không quan trọng.
    milestone = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'done')", name='ck_task_status'),
        CheckConstraint('progress >= 0 AND progress <= 100', name='ck_task_progress'),
        db.Index('ix_task_user_status_deadline', 'user_id', 'status', 'deadline'),
    )