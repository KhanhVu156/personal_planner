from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app import db, cache
from datetime import datetime, timedelta
import calendar
import os
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models import Transaction, Budget, Task
from app.services.ai_manager import request_prediction, request_training, request_prediction_batch, trigger_training_async
from app.ml.expense_model import _get_paths

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        user_id = current_user.id
        today = datetime.now()
        
        month = request.args.get('month', today.month, type=int)
        year = request.args.get('year', today.year, type=int)

        totals = db.session.query(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(Transaction.user_id == user_id).group_by(Transaction.type).all()
        
        total_income = next((float(t[1]) for t in totals if t[0] == 'income'), 0.0)
        total_expense = next((float(t[1]) for t in totals if t[0] == 'expense'), 0.0)
        balance = total_income - total_expense

        month_totals = db.session.query(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            func.extract('month', Transaction.date) == month,
            func.extract('year', Transaction.date) == year
        ).group_by(Transaction.type).all()

        income_month = next((float(t[1]) for t in month_totals if t[0] == 'income'), 0.0)
        expense_month = next((float(t[1]) for t in month_totals if t[0] == 'expense'), 0.0)

        cat_exp = db.session.query(
            Transaction.category,
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            func.extract('month', Transaction.date) == month,
            func.extract('year', Transaction.date) == year
        ).group_by(Transaction.category).all()
        
        cat_exp_dict = {cat: float(total) for cat, total in cat_exp}

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

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi Database API Dashboard: {str(e)}")
        return jsonify({'income':0,'expenses':0,'balance':0,'budgets':{},'cat_expenses':{},'tasks':[],'month':month,'year':year}), 200
    except Exception as e:
        current_app.logger.error(f"Lỗi API Dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/predict', methods=['GET'])
@login_required
def get_predictions():
    try:
        user_id = current_user.id
        target_category = 'food'
        
        paths = _get_paths(user_id)
        # Kiểm tra xem đã có đủ 4 file model chưa
        has_model = all(os.path.exists(p) for p in paths.values())
        
        # ✅ CƠ CHẾ BẤT ĐỒNG BỘ: 
        # - Nếu chưa có model -> Báo AI train ngầm, trả về 0 ngay lập tức (không bắt trình duyệt chờ)
        # - Nếu có model rồi -> Gọi AI dự đoán
        if not has_model:
            trigger_training_async(user_id)
            return jsonify({target_category: [0]*7})
        
        items = []
        for i in range(1, 8):
            future_date = datetime.now().date() + timedelta(days=i)
            items.append((future_date, target_category))
        
        # Timeout 10s: Nếu AI có model rồi, dự đoán chỉ mất < 1s. Nếu quá 10s tức là AI worker đang bận, ta cũng trả về 0 để web không bị treo.
        results = request_prediction_batch(user_id, items, timeout=10.0)
        
        if results is None:
            results = [0.0] * 7
            
        predictions = {target_category: results}
        return jsonify(predictions)
    except Exception as e:
        current_app.logger.error(f"Lỗi API Predict: {str(e)}")
        return jsonify({'food': [0]*7}), 200

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
        data = request.get_json(silent=True) or {}
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