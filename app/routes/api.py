from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db, cache
from datetime import datetime, timedelta
import calendar
from sqlalchemy import func

from app.models import Transaction, Budget, Task
from app.services.ai_manager import request_prediction, request_training

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        user_id = current_user.id
        
        # 1. Lấy giao dịch (Sử dụng order_by để tối ưu, không cần load hết nếu chỉ cần tìm tháng gần nhất)
        all_trans = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
        
        today = datetime.now()
        month, year = today.month, today.year
        
        # 2. Tìm tháng gần nhất có phát sinh giao dịch
        if not any(t.date.month == month and t.date.year == year for t in all_trans):
            if all_trans:
                # Lấy giao dịch đầu tiên (vì đã sắp xếp desc, nó là mới nhất)
                latest_date = all_trans[0].date
                month, year = latest_date.month, latest_date.year

        # 3. Tính toán bằng Python (An toàn tuyệt đối với mọi loại Database)
        income_month = 0.0
        expense_month = 0.0
        cat_exp_dict = {}
        total_income = 0.0
        total_expense = 0.0

        for t in all_trans:
            # Tính tổng cả đời
            if t.type == 'income':
                total_income += float(t.amount)
            else:
                total_expense += float(t.amount)

            # Tính toán cho tháng được chọn
            if t.date.month == month and t.date.year == year:
                if t.type == 'income':
                    income_month += float(t.amount)
                elif t.type == 'expense':
                    expense_month += float(t.amount)
                    cat_exp_dict[t.category] = cat_exp_dict.get(t.category, 0.0) + float(t.amount)

        balance = total_income - total_expense

        # 4. Lấy Ngân sách
        budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

        # 5. Lấy Tasks
        upcoming_tasks = Task.query.filter_by(user_id=user_id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
            
        tasks_data = [{
            'id': t.id, 'title': t.title, 'deadline': t.deadline.strftime('%d/%m/%Y'), 'progress': t.progress
        } for t in upcoming_tasks]

        data = {
            'income': income_month,
            'expenses': expense_month,
            'balance': balance,
            'budgets': budget_dict,
            'cat_expenses': cat_exp_dict,
            'tasks': tasks_data,
            'month': month, 
            'year': year
        }
        
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ... (Giữ nguyên các API /predict, /train, /financial-plan)