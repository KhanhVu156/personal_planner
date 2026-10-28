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
        
        # 1. THỬ LẤY TỪ CACHE TRƯỚC
        cache_key = f"user_{user_id}_stats"
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                response = jsonify(cached_data)
                response.headers['Cache-Control'] = 'no-store'
                return response
        except Exception as e:
            current_app.logger.warning(f"Lỗi đọc Cache: {e}. Sẽ truy vấn DB.")

        # 2. NẾU KHÔNG CÓ CACHE, TRUY VẤN DB
        today = datetime.now()
        month, year = today.month, today.year
        start_date = datetime(year, month, 1).date()
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day).date()

        has_trans = db.session.query(Transaction.id).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).first()

        if not has_trans:
            latest_trans = db.session.query(Transaction.date).filter_by(user_id=user_id).order_by(Transaction.date.desc()).first()
            if latest_trans:
                month, year = latest_trans.date.month, latest_trans.date.year
                start_date = datetime(year, month, 1).date()
                last_day = calendar.monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()

        # TÍNH TOÁN BẰNG SQL VÀ ÉP KIỂU FLOAT
        income_month = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar() or 0.0

        expense_month = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar() or 0.0

        total_income = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=user_id, type='income').scalar() or 0.0
        total_expense = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=user_id, type='expense').scalar() or 0.0
        balance = float(total_income) - float(total_expense)

        budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

        cat_expenses = db.session.query(
            Transaction.category, func.sum(Transaction.amount)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(Transaction.category).all()
        
        cat_exp_dict = {c[0]: float(c[1]) for c in cat_expenses if c[1] is not None}

        upcoming_tasks = Task.query.filter_by(user_id=user_id) \
            .filter(Task.status.in_(['pending', 'in_progress'])) \
            .order_by(Task.deadline.asc()).limit(5).all()
            
        tasks_data = [{
            'id': t.id, 'title': t.title, 'deadline': t.deadline.strftime('%d/%m/%Y'), 'progress': t.progress
        } for t in upcoming_tasks]

        data = {
            'income': float(income_month),
            'expenses': float(expense_month),
            'balance': balance,
            'budgets': budget_dict,
            'cat_expenses': cat_exp_dict,
            'tasks': tasks_data,
            'month': month, 
            'year': year
        }
        
        # 3. LƯU VÀO CACHE
        try:
            cache.set(cache_key, data, timeout=5)
        except Exception as e:
            current_app.logger.warning(f"Lỗi ghi Cache: {e}")

        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/predict', methods=['GET'])
@login_required
def get_predictions():
    try:
        user_id = current_user.id
        categories = ['food', 'transport', 'education', 'entertainment', 'shopping', 'bills', 'other']
        predictions = {}
        
        for cat in categories:
            cat_pred = []
            for i in range(1, 8):
                future_date = datetime.now().date() + timedelta(days=i)
                # GỌI QUA AI MANAGER
                pred = request_prediction(user_id, future_date, cat)
                cat_pred.append(pred if pred is not None else 0)
            predictions[cat] = cat_pred
            
        return jsonify(predictions)
    except Exception as e:
        current_app.logger.error(f"Lỗi API Predict: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/train', methods=['POST'])
@login_required
def train():
    try:
        success = request_training(current_user.id)
        if success:
            return jsonify({'status': 'success', 'message': 'Model trained successfully'})
        return jsonify({'status': 'error', 'message': 'Insufficient data or AI worker failed'}), 400
    except Exception as e:
        current_app.logger.error(f"Lỗi API Train: {str(e)}")
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
        current_app.logger.error(f"Lỗi API Financial Plan: {str(e)}")
        return jsonify({'error': str(e)}), 500