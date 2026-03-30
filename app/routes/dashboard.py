from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Transaction, Budget, Task
from sqlalchemy import func, extract
from datetime import datetime

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    today = datetime.utcnow()
    month, year = today.month, today.year

    income = Transaction.query.filter_by(user_id=current_user.id, type='income') \
        .filter(extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year) \
        .with_entities(func.sum(Transaction.amount)).scalar() or 0

    expenses = Transaction.query.filter_by(user_id=current_user.id, type='expense') \
        .filter(extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year) \
        .with_entities(func.sum(Transaction.amount)).scalar() or 0

    balance = Transaction.query.filter_by(user_id=current_user.id) \
        .with_entities(func.sum(Transaction.amount)).scalar() or 0

    budgets = Budget.query.filter_by(user_id=current_user.id, month=month, year=year).all()
    budget_dict = {b.category: b.amount for b in budgets}

    cat_expenses = Transaction.query.filter_by(user_id=current_user.id, type='expense') \
        .filter(extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year) \
        .with_entities(Transaction.category, func.sum(Transaction.amount)) \
        .group_by(Transaction.category).all()
    cat_exp_dict = {c[0]: c[1] for c in cat_expenses}

    upcoming_tasks = Task.query.filter_by(user_id=current_user.id, status='pending') \
        .filter(Task.deadline >= datetime.utcnow()) \
        .order_by(Task.deadline).limit(5).all()

    return render_template('index.html',
                           income=income,
                           expenses=expenses,
                           balance=balance,
                           budgets=budget_dict,
                           cat_expenses=cat_exp_dict,
                           tasks=upcoming_tasks)