from flask import Blueprint, jsonify, request   # thêm request
from flask_login import login_required, current_user
from app import db
from app.models import Transaction
from app.ml_model import predict_expense, train_model, FinancialPlanner   # thêm FinancialPlanner
from datetime import datetime, timedelta

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/predict', methods=['GET'])
@login_required
def get_predictions():
    user_id = current_user.id
    train_model(user_id, db.session)

    categories = ['food', 'transport', 'other']
    predictions = {}
    for cat in categories:
        cat_pred = []
        for i in range(1, 8):
            future_date = datetime.now().date() + timedelta(days=i)
            pred = predict_expense(user_id, future_date, cat, db.session)
            cat_pred.append(pred if pred is not None else 0)
        predictions[cat] = cat_pred
    return jsonify(predictions)

@bp.route('/train', methods=['POST'])
@login_required
def train():
    model = train_model(current_user.id, db.session)
    if model:
        return jsonify({'status': 'success', 'message': 'Model trained successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'Insufficient data for training'}), 400,
    # Thêm import
from app.ml_model import FinancialPlanner

@bp.route('/financial-plan', methods=['POST'])
@login_required
def financial_plan():
    """
    Nhận yêu cầu từ frontend, trả về kế hoạch chi tiêu tối ưu.
    Body JSON mẫu:
    {
        "monthly_income": 15000000,
        "savings_percent": 20,
        "category_weights": {"food": 1.2, "transport": 0.8, "other": 1.0}
    }
    """
    data = request.get_json()
    monthly_income = data.get('monthly_income')
    if not monthly_income or monthly_income <= 0:
        return jsonify({'error': 'Invalid monthly income'}), 400

    savings_percent = data.get('savings_percent')
    savings_goal = data.get('savings_goal')
    category_weights = data.get('category_weights')

    planner = FinancialPlanner(current_user.id, db.session)
    suggestion = planner.suggest_budgets(
        monthly_income,
        savings_goal=savings_goal,
        savings_percent=savings_percent,
        category_weights=category_weights
    )
    return jsonify(suggestion)