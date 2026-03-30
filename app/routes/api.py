from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Transaction
from app.ml_model import predict_expense, train_model
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
        return jsonify({'status': 'error', 'message': 'Insufficient data for training'}), 400