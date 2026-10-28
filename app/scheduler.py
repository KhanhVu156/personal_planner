from flask import current_app
from flask_mail import Message
from sqlalchemy import func
from app import mail, db, cache
from app.models import User, Task, Budget, Transaction
from datetime import datetime, timedelta
import calendar
import logging

# ✅ FIX P1: dedup bằng Redis Cache — không bị reset khi Render restart
def _already_sent_today(key: str) -> bool:
    return cache.get(f'sent_mail_{key}') == '1'

def _mark_sent(key: str):
    # Lưu trạng thái đã gửi trong 24 giờ (86400 giây)
    cache.set(f'sent_mail_{key}', '1', timeout=86400)

def check_deadlines():
    """Gửi email nhắc task sắp đến hạn (trong 24h tới). Mỗi task 1 email/ngày."""
    with current_app.app_context():
        now = datetime.now()
        soon = now + timedelta(days=1)

        tasks = Task.query.filter(
            Task.status != 'done',
            Task.deadline <= soon,
            Task.deadline > now,
        ).all()

        for task in tasks:
            key = f'task:{task.id}'
            if _already_sent_today(key):
                continue

            user = db.session.get(User, task.user_id)
            if not (user and user.email):
                continue

            msg = Message(
                'Cảnh báo: Công việc sắp đến hạn!',
                recipients=[user.email],
            )
            msg.body = (
                f"Chào {user.username},\n\n"
                f"Công việc '{task.title}' của bạn sẽ đến hạn vào lúc "
                f"{task.deadline.strftime('%H:%M ngày %d/%m/%Y')}. "
                f"Vui lòng hoàn thành đúng hạn.\n\n"
                f"Trân trọng,\nPersonal Planner."
            )
            try:
                mail.send(msg)
                _mark_sent(key)
            except Exception as e:
                logging.error(f"Failed to send email for task {task.id}: {e}")


def check_budgets():
    """Gửi email cảnh báo vượt ngân sách. Mỗi (user, category) 1 email/ngày."""
    with current_app.app_context():
        now = datetime.now()
        month, year = now.month, now.year

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        users = User.query.all()
        for user in users:
            budgets = Budget.query.filter_by(
                user_id=user.id, month=month, year=year
            ).all()
            if not budgets:
                continue

            cats = [b.category for b in budgets]
            rows = db.session.query(
                Transaction.category,
                func.coalesce(func.sum(Transaction.amount), 0),
            ).filter(
                Transaction.user_id == user.id,
                Transaction.type == 'expense',
                Transaction.category.in_(cats),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            ).group_by(Transaction.category).all()
            spent_by_cat = {cat: float(total) for cat, total in rows}

            for b in budgets:
                spent = spent_by_cat.get(b.category, 0.0)
                if spent <= float(b.amount):
                    continue

                key = f'budget:{user.id}:{b.category}:{year}-{month:02d}'
                if _already_sent_today(key):
                    continue
                if not user.email:
                    continue

                msg = Message(
                    'Cảnh báo: Vượt quá ngân sách!',
                    recipients=[user.email],
                )
                msg.body = (
                    f"Chào {user.username},\n\n"
                    f"Bạn đã chi tiêu {spent:,.0f} VND cho danh mục '{b.category}' "
                    f"trong tháng này, vượt quá mức ngân sách "
                    f"{float(b.amount):,.0f} VND mà bạn đã đặt ra.\n\n"
                    f"Hãy kiểm tra lại chi tiêu của mình nhé!\n\n"
                    f"Trân trọng,\nPersonal Planner."
                )
                try:
                    mail.send(msg)
                    _mark_sent(key)
                except Exception as e:
                    logging.error(
                        f"Failed to send budget alert email to {user.email}: {e}"
                    )