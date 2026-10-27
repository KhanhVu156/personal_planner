import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

# Tắt các cảnh báo rác của TensorFlow và ÉP CHỈ CHẠY 1 LUỒNG CPU (Giảm RAM)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

# Trỏ đường dẫn lưu model vào thư mục app/static/models
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'static', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Bộ nhớ đệm (Cache) để lưu model đã load
_model_cache = {}

def _get_paths(user_id):
    return {
        'model': os.path.join(MODEL_DIR, f'expense_model_{user_id}.keras'), 
        'scaler': os.path.join(MODEL_DIR, f'scaler_{user_id}.pkl'),
        'encoder': os.path.join(MODEL_DIR, f'encoder_{user_id}.pkl')
    }

def prepare_data(transactions, user_id):
    df = pd.DataFrame(transactions)
    df = df[df['type'] == 'expense'].copy()
    if df.empty:
        return None, None
    
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
    
    paths = _get_paths(user_id)
    joblib.dump(scaler, paths['scaler'])
    joblib.dump(le, paths['encoder'])
    
    return X_scaled, y

def build_model(input_dim):
    # Import muộn (Lazy Import) để tiết kiệm RAM khi không dùng AI
    import keras
    from keras import layers
    
    model = keras.Sequential([
        layers.Dense(32, activation='relu', input_shape=(input_dim,)), # Giảm từ 64 -> 32 để nhẹ hơn
        layers.Dropout(0.2),
        layers.Dense(16, activation='relu'), # Giảm từ 32 -> 16
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train_model(user_id, db_session):
    from app.models import Transaction
    
    # Nếu cache quá lớn (nhiều user cùng dùng), xóa bớt để giải phóng RAM
    if len(_model_cache) > 5:
        _model_cache.clear()
        print("Đã xóa Cache AI để giải phóng RAM.")
        
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    
    if not transactions or len(transactions) < 10:
        return None
        
    data = [{'date': t.date, 'amount': float(t.amount), 'category': t.category, 'type': t.type} for t in transactions]
    X, y = prepare_data(data, user_id)
    
    if X is None:
        return None
        
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = build_model(X.shape[1])
        # Giảm epochs từ 50 -> 20 để train nhanh và ít tốn RAM hơn
        model.fit(X_train, y_train, epochs=20, batch_size=16, validation_data=(X_test, y_test), verbose=0)
        
        model.save(_get_paths(user_id)['model'])
        
        _model_cache[user_id] = {
            'model': model,
            'scaler': joblib.load(_get_paths(user_id)['scaler']),
            'encoder': joblib.load(_get_paths(user_id)['encoder'])
        }
        return model
    except Exception as e:
        print(f"Lỗi khi train model (Có thể do hết RAM): {e}")
        return None

def predict_expense(user_id, future_date, category, db_session):
    paths = _get_paths(user_id)
    
    # Import muộn TensorFlow và Keras
    import keras
    
    if user_id in _model_cache:
        model_data = _model_cache[user_id]
        model = model_data['model']
        scaler = model_data['scaler']
        le = model_data['encoder']
    else:
        if not os.path.exists(paths['model']):
            train_model(user_id, db_session)
            if not os.path.exists(paths['model']):
                return 0.0 
                
        try:
            model = keras.models.load_model(paths['model'])
            scaler = joblib.load(paths['scaler'])
            le = joblib.load(paths['encoder'])
            _model_cache[user_id] = {'model': model, 'scaler': scaler, 'encoder': le}
        except Exception as e:
            print(f"Lỗi load model: {e}")
            return 0.0

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
    
    return max(0, float(prediction))