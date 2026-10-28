from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Numeric
from app import db

# ✅ FIX P1: Sử dụng timezone-aware datetime thay cho utcnow (deprecated)
def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date(), index=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(Numeric(30, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index('ix_trans_user_date', 'user_id', 'date'),
        db.Index('ix_trans_user_type_date', 'user_id', 'type', 'date'),
        db.Index('ix_trans_user_category_date', 'user_id', 'category', 'date'),
    )


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    month = db.Column(db.Integer, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    amount = db.Column(Numeric(30, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', 'month', 'year', name='uq_budget_user_cat_ym'),
        db.Index('ix_budget_user_ym', 'user_id', 'month', 'year'),
    )


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', index=True)
    progress = db.Column(db.Integer, default=0)
    milestone = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index('ix_task_user_status_deadline', 'user_id', 'status', 'deadline'),
    )