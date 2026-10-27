from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from datetime import datetime, timedelta
import calendar
import time
from sqlalchemy import func

from app.models import Transaction, Budget, Task

bp = Blueprint('api', __name__, url_prefix='/api')

# Bộ đệm lưu trữ API
_api_cache = {}

@bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    user_id = current_user.id
    now = time.time()
    
    # 1. Kiểm tra Cache (Nếu có và chưa quá 2 giây)
    if user_id in _api_cache:
        cached_time, cached_data = _api_cache[user_id]
        if now - cached_time < 2.0:
            response = jsonify(cached_data)
            response.headers['Cache-Control'] = 'no-store'
            return response

    # 2. Nếu không có Cache, truy vấn Database
    try:
        today = datetime.now()
        month, year = today.month, today.year

        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        has_trans = Transaction.query.filter_by(user_id=current_user.id) \
            .filter(Transaction.date >= start_date, Transaction.date <= end_date).first()

        if not has_trans:
            latest_trans = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).first()
            if latest_trans:
                month, year = latest_trans.date.month, latest_trans.date.year
                start_date = datetime(year, month, 1).date()
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()

        trans_in_month = Transaction.query.filter_by(user_id=current_user.id) \
            .filter(Transaction.date >= start_date, Transaction.date <= end_date).all()

        income = sum(float(t.amount) for t in trans_in_month if t.type == 'income')
        expenses = sum(float(t.amount) for t in trans_in_month if t.type == 'expense')

        total_trans = Transaction.query.filter_by(user_id=current_user.id).all()
        total_income = sum(float(t.amount) for t in total_trans if t.type == 'income')
        total_expense = sum(float(t.amount) for t in total_trans if t.type == 'expense')
        balance = total_income - total_expense

        budgets = Budget.query.filter_by(user_id=current_user.id, month=month, year=year).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

        cat_exp_dict = {}
        for t in trans_in_month:
            if t.type == 'expense':
                cat_exp_dict[t.category] = cat_exp_dict.get(t.category, 0.0) + float(t.amount)

        upcoming_tasks = Task.query.filter_by(user_id=current_user.id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
            
        tasks_data = [{
            'id': t.id, 'title': t.title, 'deadline': t.deadline.strftime('%d/%m/%Y'), 'progress': t.progress
        } for t in upcoming_tasks]

        data = {
            'income': income,
            'expenses': expenses,
            'balance': balance,
            'budgets': budget_dict,
            'cat_expenses': cat_exp_dict,
            'tasks': tasks_data,
            'month': month, 
            'year': year
        }
        
        # 3. Lưu vào Cache
        _api_cache[user_id] = (now, data)
        
        # Giới hạn Cache (Nếu có quá nhiều User, xóa bớt để giải phóng RAM)
        if len(_api_cache) > 20:
            _api_cache.clear()

        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ----- CÁC API CỦA AI -----
@bp.route('/predict', methods=['GET'])
@login_required
def get_predictions():
    try:
        from app.ml.expense_model import predict_expense, train_model
        user_id = current_user.id
        train_model(user_id, db.session)
        categories = ['food', 'transport', 'education', 'entertainment', 'shopping', 'bills', 'other'] # Cập nhật danh mục mới
        predictions = {}
        for cat in categories:
            cat_pred = []
            for i in range(1, 8):
                future_date = datetime.now().date() + timedelta(days=i)
                pred = predict_expense(user_id, future_date, cat, db.session)
                cat_pred.append(pred if pred is not None else 0)
            predictions[cat] = cat_pred
        return jsonify(predictions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/train', methods=['POST'])
@login_required
def train():
    try:
        from app.ml.expense_model import train_model
        model = train_model(current_user.id, db.session)
        if model:
            return jsonify({'status': 'success', 'message': 'Model trained successfully'})
        return jsonify({'status': 'error', 'message': 'Insufficient data for training'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    try:
        from app.services.financial_planner import FinancialPlanner
        data = request.get_json()
        if not data: return jsonify({'error': 'Missing JSON data'}), 400
        monthly_income = data.get('monthly_income')
        if not monthly_income or monthly_income <= 0: return jsonify({'error': 'Invalid monthly income'}), 400

        planner = FinancialPlanner(current_user.id, db.session)
        suggestion = planner.suggest_budgets(
            monthly_income, savings_goal=data.get('savings_goal'),
            savings_percent=data.get('savings_percent'), category_weights=data.get('category_weights')
        )
        return jsonify(suggestion)
    except Exception as e:
        return jsonify({'error': str(e)}), 500