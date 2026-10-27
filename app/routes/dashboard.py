from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Transaction, Budget, Task
from app import db # Bổ sung import db
from sqlalchemy import func
from datetime import datetime
import calendar

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    today = datetime.now()
    month, year = today.month, today.year

    start_date = datetime(year, month, 1).date()
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day).date()

    # TỐI ƯU 1: Chỉ query ID thay vì lấy toàn bộ object
    has_trans = db.session.query(Transaction.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).first()

    if not has_trans:
        # TỐI ƯU 2: Chỉ lấy ngày tháng của giao dịch mới nhất, không lấy cả object
        latest_trans = db.session.query(Transaction.date).filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).first()
        if latest_trans:
            month, year = latest_trans.date.month, latest_trans.date.year
            start_date = datetime(year, month, 1).date()
            last_day = calendar.monthrange(year, month)[1]
            end_date = datetime(year, month, last_day).date()

    # Đồng bộ lấy Task
    upcoming_tasks = Task.query.filter_by(user_id=current_user.id) \
        .filter(Task.status.in_(['pending', 'in_progress'])) \
        .order_by(Task.deadline.asc()).limit(5).all()

    return render_template('dashboard/index.html',
                           display_month=month,
                           display_year=year,
                           tasks=upcoming_tasks)