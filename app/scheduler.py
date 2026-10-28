from flask import current_app
from flask_mail import Message
from sqlalchemy import func
from app import mail, db, cache
from app.models import User, Task, Budget, Transaction
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar
import logging


# ✅ TƯ DUY XỬ LÝ TIMEZONE (CRITICAL FIX):
# - Server (Render) chạy giờ UTC (chậm hơn VN 7 tiếng).
# - Task.deadline lưu giờ VN (do user nhập).
# - Nếu dùng datetime.now() trên server để so sánh với Task.deadline, 
#   sẽ bị lệch 7 tiếng -> Scheduler chạy sai giờ hoặc bỏ sót task.
# - Giải pháp: Ép mọi tính toán "hiện tại" trong Scheduler phải dùng giờ VN.
VN_TZ = ZoneInfo('Asia/Ho_Chi_Minh')


def _vn_now():
    """Trả về thời gian hiện tại theo múi giờ Việt Nam (Naive datetime)."""
    return datetime.now(VN_TZ).replace(tzinfo=None)


def _already_sent_today(key: str) -> bool:
    """
    Kiểm tra xem email đã được gửi hôm nay chưa bằng Cache.
    TƯ DUY: Scheduler chạy định kỳ (VD: mỗi 15 phút). Dùng Cache để tránh gửi spam.
    """
    return cache.get(f'sent_mail_{key}') == '1'


def _mark_sent(key: str):
    """Đánh dấu đã gửi email, lưu trong Cache 24 giờ (86400 giây)."""
    cache.set(f'sent_mail_{key}', '1', timeout=86400)


def check_deadlines():
    """Gửi email nhắc task sắp đến hạn (trong 24h tới). Mỗi task 1 email/ngày."""
    with current_app.app_context():
        now = _vn_now() # ✅ Dùng giờ VN để so sánh
        soon = now + timedelta(days=1)

        # Tối ưu Query: Lọc trực tiếp dưới DB (Sử dụng Index trên cột deadline)
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
        now = _vn_now() # ✅ Dùng giờ VN để xác định tháng/năm hiện tại
        month, year = now.month, now.year

        # Tối ưu Date Range: Dùng start_date và end_date thay vì hàm extract() 
        # để tận dụng Index trên cột Transaction.date.
        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        users = User.query.all()
        for user in users:
            budgets = Budget.query.filter_by(user_id=user.id, month=month, year=year).all()
            if not budgets:
                continue

            cats = [b.category for b in budgets]
            
            # Tối ưu N+1 Query: Query 1 lần duy nhất lấy tổng chi tiêu của tất cả các category
            rows = db.session.query(
                Transaction.category,
                func.coalesce(func.sum(Transaction.amount), 0),
            ).filter(
                Transaction.user_id == user.id,
                Transaction.type == 'expense',
                Transaction.category.in_(cats),
                Transaction.date >= start_date, # ✅ Dùng Range Query
                Transaction.date <= end_date,
            ).group_by(Transaction.category).all()
            
            spent_by_cat = {cat: float(total) for cat, total in rows}

            for b in budgets:
                spent = spent_by_cat.get(b.category, 0.0)
                if spent <= float(b.amount):
                    continue # Chưa vượt ngân sách

                key = f'budget:{user.id}:{b.category}:{year}-{month:02d}'
                if _already_sent_today(key):
                    continue
                if not user.email:
                    continue

                msg = Message('Cảnh báo: Vượt quá ngân sách!', recipients=[user.email])
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
                    logging.error(f"Failed to send budget alert email to {user.email}: {e}")