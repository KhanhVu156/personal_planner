from flask import current_app
from flask_mail import Message
from app import mail
from app.models import User, Task, Budget, Transaction
from datetime import datetime, timedelta
import calendar
import logging

def check_deadlines():
    with current_app.app_context():
        tomorrow = datetime.now() + timedelta(days=1)
        # Tìm task sắp đến hạn trong 1 ngày tới và chưa hoàn thành
        tasks = Task.query.filter(Task.status != 'done', Task.deadline <= tomorrow, Task.deadline > datetime.now()).all()
        
        for task in tasks:
            user = User.query.get(task.user_id)
            if user and user.email:
                msg = Message('Cảnh báo: Công việc sắp đến hạn!', recipients=[user.email])
                msg.body = f"Chào {user.username},\n\nCông việc '{task.title}' của bạn sẽ đến hạn vào lúc {task.deadline.strftime('%H:%M ngày %d/%m/%Y')}. Vui lòng hoàn thành đúng hạn.\n\nTrân trọng,\nPersonal Planner."
                try:
                    mail.send(msg)
                except Exception as e:
                    logging.error(f"Failed to send email for task {task.id}: {e}")

def check_budgets():
    with current_app.app_context():
        now = datetime.now()
        month, year = now.month, now.year
        
        # Tính ngày đầu tháng và ngày cuối tháng
        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        users = User.query.all()
        for user in users:
            budgets = Budget.query.filter_by(user_id=user.id, month=month, year=year).all()
            for b in budgets:
                # TỐI ƯU: Lấy giao dịch ra và tính bằng Python để tránh lỗi SQLite sum()
                trans = Transaction.query.filter_by(user_id=user.id, type='expense', category=b.category) \
                    .filter(Transaction.date >= start_date, Transaction.date <= end_date).all()
                spent = sum(float(t.amount) for t in trans)
                
                if spent > float(b.amount):
                    if user.email:
                        msg = Message('Cảnh báo: Vượt quá ngân sách!', recipients=[user.email])
                        msg.body = f"Chào {user.username},\n\nBạn đã chi tiêu {spent:,.0f} VND cho danh mục '{b.category}' trong tháng này, vượt quá mức ngân sách {float(b.amount):,.0f} VND mà bạn đã đặt ra.\n\nHãy kiểm tra lại chi tiêu của mình nhé!\n\nTrân trọng,\nPersonal Planner."
                        try:
                            mail.send(msg)
                        except Exception as e:
                            logging.error(f"Failed to send budget alert email to {user.email}: {e}")