from flask import current_app
from sqlalchemy import func
from app import db, cache, send_email
from app.models import User, Task, Budget, Transaction
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import calendar

# TƯ DUY XỬ LÝ TIMEZONE (CRITICAL FIX):
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


# Dictionary ánh xạ tên danh mục từ tiếng Anh sang tiếng Việt để hiển thị trong email
CATEGORY_MAP = {
    'food': 'Ăn uống',
    'transport': 'Di chuyển',
    'education': 'Học tập',
    'entertainment': 'Giải trí',
    'shopping': 'Mua sắm',
    'bills': 'Hóa đơn',
    'other': 'Khác',
    'salary': 'Lương'
}


def check_deadlines():
    """Gửi email nhắc task sắp đến hạn (trong 24h tới). Mỗi task 1 email/ngày."""
    with current_app.app_context():
        now = _vn_now()
        soon = now + timedelta(days=1)
        
        # TƯ DUY TỐI ƯU: Sử dụng ngày hiện tại làm một phần của key cache.
        # Điều này đảm bảo dù Scheduler chạy lúc 23h59 hôm nay, thì 0h01 ngày mai nó vẫn gửi được mail mới.
        today_str = now.strftime('%Y-%m-%d')

        try:
            # TƯ DUY TỐI ƯU QUERY: Sử dụng JOIN để lấy thông tin User cùng lúc với Task.
            # Tránh lỗi N+1 Query (gọi database 1000 lần nếu có 1000 task).
            # Đồng thời, lấy cả các task đã quá hạn (deadline < now) để nhắc nhở.
            results = db.session.query(Task, User).join(User, Task.user_id == User.id).filter(
                Task.status.in_(['pending', 'in_progress']), # Chỉ nhắc task chưa hoàn thành
                Task.deadline <= soon, # Lấy cả task quá hạn và task trong 24h tới
                User.email.isnot(None) # Chỉ lấy user có email
            ).all()
        except Exception as e:
            current_app.logger.error(f"Lỗi truy vấn Database trong check_deadlines: {e}")
            return

        for task, user in results:
            # Key bao gồm ngày cụ thể, đảm bảo 1 ngày chỉ gửi 1 lần cho task này
            key = f'task:{task.id}:{today_str}'
            if _already_sent_today(key):
                continue

            # Xác định xem task đã quá hạn chưa để đổi nội dung email
            is_overdue = task.deadline < now
            
            subject = 'Cảnh báo: Công việc đã quá hạn!' if is_overdue else 'Cảnh báo: Công việc sắp đến hạn!'
            time_msg = 'đã quá hạn vào lúc' if is_overdue else 'sẽ đến hạn vào lúc'
            color = '#ef4444' if is_overdue else '#f59e0b'

            html_content = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                <h3 style="color: {color};">{subject}</h3>
                <p>Chào <strong>{user.username}</strong>,</p>
                <p>Công việc <strong>"{task.title}"</strong> của bạn {time_msg} <strong>{task.deadline.strftime('%H:%M ngày %d/%m/%Y')}</strong>.</p>
                <p>Vui lòng kiểm tra và cập nhật tiến độ công việc để không bỏ lỡ nhé.</p>
                <br>
                <p style="font-size: 13px; color: #6b7280;">Trân trọng,<br>Personal Planner.</p>
            </div>
            """
            text_content = f"Chào {user.username},\n\nCông việc '{task.title}' của bạn {time_msg} {task.deadline.strftime('%H:%M ngày %d/%m/%Y')}. Vui lòng kiểm tra và cập nhật tiến độ.\n\nTrân trọng,\nPersonal Planner."

            # Gọi hàm send_email dùng chung
            if send_email(subject, user.email, html_content, text_content):
                _mark_sent(key)


def check_budgets():
    """Gửi email cảnh báo vượt ngân sách. Mỗi (user, category) 1 email/ngày."""
    with current_app.app_context():
        now = _vn_now()
        month, year = now.month, now.year
        today_str = now.strftime('%Y-%m-%d')

        # Tối ưu Date Range: Dùng start_date và end_date thay vì hàm extract() 
        # để tận dụng Index trên cột Transaction.date.
        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        try:
            users = User.query.all()
        except Exception as e:
            current_app.logger.error(f"Lỗi truy vấn User trong check_budgets: {e}")
            return

        for user in users:
            # Bọc từng user trong try-except để nếu 1 user lỗi, các user khác vẫn được xử lý
            try:
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
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                ).group_by(Transaction.category).all()
                
                spent_by_cat = {cat: float(total) for cat, total in rows}

                for b in budgets:
                    spent = spent_by_cat.get(b.category, 0.0)
                    if spent <= float(b.amount):
                        continue # Chưa vượt ngân sách

                    # Key bao gồm ngày cụ thể để đảm bảo gửi đúng 1 lần/ngày
                    key = f'budget:{user.id}:{b.category}:{today_str}'
                    if _already_sent_today(key):
                        continue
                    if not user.email:
                        continue

                    # Sử dụng Dictionary để dịch tên danh mục sang tiếng Việt
                    cat_name = CATEGORY_MAP.get(b.category, b.category)
                    
                    subject = 'Cảnh báo: Vượt quá ngân sách!'
                    html_content = f"""
                    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                        <h3 style="color: #ef4444;">{subject}</h3>
                        <p>Chào <strong>{user.username}</strong>,</p>
                        <p>Bạn đã chi tiêu <strong style="color: #ef4444;">{spent:,.0f} VND</strong> cho danh mục <strong>'{cat_name}'</strong> trong tháng này.</p>
                        <p>Số tiền này đã vượt quá mức ngân sách <strong>{float(b.amount):,.0f} VND</strong> mà bạn đã đặt ra.</p>
                        <p>Hãy kiểm tra lại chi tiêu của mình nhé!</p>
                        <br>
                        <p style="font-size: 13px; color: #6b7280;">Trân trọng,<br>Personal Planner.</p>
                    </div>
                    """
                    text_content = f"Chào {user.username},\n\nBạn đã chi tiêu {spent:,.0f} VND cho danh mục '{cat_name}' trong tháng này, vượt quá mức ngân sách {float(b.amount):,.0f} VND mà bạn đã đặt ra.\n\nHãy kiểm tra lại chi tiêu của mình nhé!\n\nTrân trọng,\nPersonal Planner."
                    
                    # Gọi hàm send_email dùng chung
                    if send_email(subject, user.email, html_content, text_content):
                        _mark_sent(key)
            except Exception as e:
                current_app.logger.error(f"Lỗi xử lý ngân sách cho user {user.id}: {e}")
                continue