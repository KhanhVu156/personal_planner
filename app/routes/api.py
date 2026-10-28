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
        all_trans = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
        
        today = datetime.now()
        month, year = today.month, today.year
        
        if not any(t.date.month == month and t.date.year == year for t in all_trans):
            if all_trans:
                latest_date = all_trans[0].date
                month, year = latest_date.month, latest_date.year

        income_month = 0.0
        expense_month = 0.0
        cat_exp_dict = {}
        total_income = 0.0
        total_expense = 0.0

        for t in all_trans:
            if t.type == 'income':
                total_income += float(t.amount)
            else:
                total_expense += float(t.amount)

            if t.date.month == month and t.date.year == year:
                if t.type == 'income':
                    income_month += float(t.amount)
                elif t.type == 'expense':
                    expense_month += float(t.amount)
                    cat_exp_dict[t.category] = cat_exp_dict.get(t.category, 0.0) + float(t.amount)

        balance = total_income - total_expense

        # SỬA LỖI: Ép kiểu int cho month, year khi query Budget
        budgets = Budget.query.filter_by(user_id=user_id, month=int(month), year=int(year)).all()
        budget_dict = {b.category: float(b.amount) for b in budgets}

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
                pred = request_prediction(user_id, future_date, cat)
                cat_pred.append(pred if pred is not None else 0)
            predictions[cat] = cat_pred
            
        return jsonify(predictions)
    except Exception as e:
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
        return jsonify({'error': str(e)}), 500

@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    try:
        from app.services.financial_planner import FinancialPlanner
        data = request.get_json()
        if not data: 
            return jsonify({'error': 'Dữ liệu gửi lên bị trống'}), 400
            
        monthly_income = data.get('monthly_income')
        if not monthly_income or monthly_income <= 0: 
            return jsonify({'error': 'Thu nhập không hợp lệ'}), 400

        planner = FinancialPlanner(current_user.id, db.session)
        suggestion = planner.suggest_budgets(
            monthly_income, 
            savings_goal=data.get('savings_goal'),
            savings_percent=data.get('savings_percent'), 
            category_weights=data.get('category_weights')
        )
        return jsonify(suggestion)
    except Exception as e:
        current_app.logger.error(f"Lỗi API Financial Plan: {str(e)}")
        return jsonify({'error': f"Lỗi máy chủ: {str(e)}"}), 500