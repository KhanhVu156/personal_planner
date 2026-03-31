import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import tensorflow as tf
import keras
from keras import layers
import joblib

MODEL_DIR = 'models'
MODEL_PATH = os.path.join(MODEL_DIR, 'expense_model.h5')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
ENCODER_PATH = os.path.join(MODEL_DIR, 'encoder.pkl')

os.makedirs(MODEL_DIR, exist_ok=True)

# ---------------------- ML prediction (giữ nguyên) ----------------------
def prepare_data(transactions):
    df = pd.DataFrame(transactions)
    df = df[df['type'] == 'expense'].copy()
    if df.empty:
        return None, None, None, None
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.dayofweek
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    le = LabelEncoder()
    df['category_encoded'] = le.fit_transform(df['category'])
    features = ['day_of_week', 'day_of_month', 'month', 'year', 'category_encoded']
    X = df[features].values
    y = df['amount'].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(le, ENCODER_PATH)
    return X_scaled, y, scaler, le

def build_model(input_dim):
    model = keras.Sequential([
        layers.Dense(64, activation='relu', input_shape=(input_dim,)),
        layers.Dropout(0.2),
        layers.Dense(32, activation='relu'),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train_model(user_id, db_session):
    from app.models import Transaction
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    if not transactions:
        return None
    data = [{
        'date': t.date,
        'amount': t.amount,
        'category': t.category,
        'type': t.type
    } for t in transactions]
    X, y, _, _ = prepare_data(data)
    if X is None or len(X) < 10:
        return None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = build_model(X.shape[1])
    model.fit(X_train, y_train, epochs=50, batch_size=16, validation_data=(X_test, y_test), verbose=0)
    model.save(MODEL_PATH)
    return model

def predict_expense(user_id, future_date, category, db_session):
    if not os.path.exists(MODEL_PATH):
        train_model(user_id, db_session)
        if not os.path.exists(MODEL_PATH):
            return None
    model = keras.models.load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    le = joblib.load(ENCODER_PATH)
    try:
        cat_encoded = le.transform([category])[0]
    except ValueError:
        cat_encoded = 0
    features = np.array([[
        future_date.weekday(),
        future_date.day,
        future_date.month,
        future_date.year,
        cat_encoded
    ]])
    features_scaled = scaler.transform(features)
    prediction = model.predict(features_scaled, verbose=0)[0][0]
    return max(0, prediction)

# ---------------------- Financial Planner mới ----------------------
class FinancialPlanner:
    """
    Lập kế hoạch chi tiêu tối ưu dựa trên thu nhập, mục tiêu tiết kiệm và lịch sử chi tiêu.
    """
    def __init__(self, user_id, db_session):
        self.user_id = user_id
        self.db_session = db_session
        self.historical_expenses = self._get_historical_expenses()
        self.categories = ['food', 'transport', 'other']

    def _get_historical_expenses(self):
        """Lấy dữ liệu chi tiêu trung bình theo danh mục từ các giao dịch đã ghi."""
        from app.models import Transaction
        from sqlalchemy import func
        expenses = {}
        for cat in self.categories:
            avg = Transaction.query.filter_by(
                user_id=self.user_id,
                type='expense',
                category=cat
            ).with_entities(func.avg(Transaction.amount)).scalar()
            expenses[cat] = avg if avg else 0
        return expenses

    def suggest_budgets(self, monthly_income, savings_goal=None, savings_percent=None,
                        category_weights=None):
        """
        Đề xuất ngân sách cho từng danh mục.

        Tham số:
        - monthly_income: float, thu nhập hàng tháng
        - savings_goal: float (tùy chọn), số tiền muốn tiết kiệm
        - savings_percent: float (tùy chọn), phần trăm thu nhập muốn tiết kiệm (0-100)
        - category_weights: dict, trọng số ưu tiên cho từng danh mục (mặc định dựa trên lịch sử)

        Trả về:
        - dict: ngân sách đề xuất cho từng danh mục và số tiền tiết kiệm.
        """
        # Xác định số tiền tiết kiệm
        if savings_goal is not None:
            target_savings = savings_goal
        elif savings_percent is not None:
            target_savings = monthly_income * (savings_percent / 100.0)
        else:
            target_savings = monthly_income * 0.2  # mặc định tiết kiệm 20%

        # Đảm bảo tiết kiệm không vượt quá thu nhập
        target_savings = min(target_savings, monthly_income)

        remaining = monthly_income - target_savings

        # Nếu không có lịch sử chi tiêu, dùng tỷ lệ mặc định
        if sum(self.historical_expenses.values()) == 0:
            default_weights = {'food': 0.4, 'transport': 0.2, 'other': 0.4}
            budgets = {}
            for cat in self.categories:
                budgets[cat] = remaining * default_weights.get(cat, 0.2)
        else:
            # Sử dụng tỷ lệ dựa trên lịch sử, có thể điều chỉnh bởi category_weights
            total_hist = sum(self.historical_expenses.values())
            base_ratios = {cat: self.historical_expenses[cat] / total_hist for cat in self.categories}
            if category_weights:
                # Điều chỉnh trọng số theo yêu cầu người dùng
                for cat, weight in category_weights.items():
                    if cat in base_ratios:
                        base_ratios[cat] *= weight
                # Chuẩn hóa lại tổng = 1
                total = sum(base_ratios.values())
                for cat in base_ratios:
                    base_ratios[cat] /= total

            budgets = {}
            for cat in self.categories:
                budgets[cat] = remaining * base_ratios[cat]

        # Làm tròn và đảm bảo không âm
        for cat in budgets:
            budgets[cat] = round(budgets[cat], 2)

        return {
            'savings': round(target_savings, 2),
            'budgets': budgets
        }

    def get_current_spending(self, month=None, year=None):
        """Lấy tổng chi tiêu thực tế trong tháng hiện tại (hoặc tháng chỉ định)."""
        from app.models import Transaction
        from sqlalchemy import func
        from datetime import datetime

        if month is None:
            now = datetime.utcnow()
            month = now.month
            year = now.year

        total_by_cat = {}
        for cat in self.categories:
            total = Transaction.query.filter_by(
                user_id=self.user_id,
                type='expense',
                category=cat
            ).filter(
                Transaction.date >= datetime(year, month, 1),
                Transaction.date < datetime(year, month + 1, 1) if month < 12 else datetime(year+1, 1, 1)
            ).with_entities(func.sum(Transaction.amount)).scalar() or 0
            total_by_cat[cat] = total
        return total_by_cat

    def compare_with_suggestion(self, monthly_income, savings_goal=None, savings_percent=None,
                                 category_weights=None, month=None, year=None):
        """
        So sánh chi tiêu thực tế với ngân sách đề xuất.
        """
        suggestion = self.suggest_budgets(monthly_income, savings_goal, savings_percent, category_weights)
        actual = self.get_current_spending(month, year)
        comparison = {}
        for cat in self.categories:
            diff = actual.get(cat, 0) - suggestion['budgets'][cat]
            comparison[cat] = {
                'suggested': suggestion['budgets'][cat],
                'actual': actual.get(cat, 0),
                'difference': diff,
                'status': 'over' if diff > 0 else 'under' if diff < 0 else 'on_track'
            }
        return {
            'savings': suggestion['savings'],
            'comparison': comparison
        }