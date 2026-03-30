from flask import current_app
from flask_mail import Message
from app import mail
from app.models import User, Task, Budget, Transaction
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import logging

def check_deadlines():
    with current_app.app_context():
        tomorrow = datetime.utcnow() + timedelta(days=1)
        tasks = Task.query.filter(Task.status != 'done', Task.deadline <= tomorrow, Task.deadline > datetime.utcnow()).all()
        for task in tasks:
            user = User.query.get(task.user_id)
            if user and user.email:
                msg = Message('Task deadline approaching', recipients=[user.email])
                msg.body = f"Your task '{task.title}' is due on {task.deadline.strftime('%Y-%m-%d %H:%M')}. Please complete it."
                try:
                    mail.send(msg)
                except Exception as e:
                    logging.error(f"Failed to send email: {e}")

def check_budgets():
    with current_app.app_context():
        now = datetime.utcnow()
        month, year = now.month, now.year
        users = User.query.all()
        for user in users:
            budgets = Budget.query.filter_by(user_id=user.id, month=month, year=year).all()
            for b in budgets:
                spent = Transaction.query.filter_by(user_id=user.id, type='expense', category=b.category) \
                    .filter(extract('month', Transaction.date) == month,
                            extract('year', Transaction.date) == year) \
                    .with_entities(func.sum(Transaction.amount)).scalar() or 0
                if spent > b.amount:
                    if user.email:
                        msg = Message('Budget exceeded', recipients=[user.email])
                        msg.body = f"You've spent {spent:.2f} VND on {b.category} this month, exceeding your budget {b.amount:.2f} VND."
                        mail.send(msg)