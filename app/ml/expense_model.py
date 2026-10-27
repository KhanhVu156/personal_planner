import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

# Tắt cảnh báo rác
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

# Trỏ đường dẫn lưu model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'static', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Bộ nhớ đệm (Cache)
_model_cache = {}

def _get_paths(user_id):
    return {
        # ĐỔI ĐUÔI FILE SANG .tflite CHO SIÊU NHẸ
        'model': os.path.join(MODEL_DIR, f'expense_model_{user_id}.tflite'), 
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
    import keras
    from keras import layers
    
    model = keras.Sequential([
        layers.Dense(32, activation='relu', input_shape=(input_dim,)),
        layers.Dropout(0.2),
        layers.Dense(16, activation='relu'),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train_model(user_id, db_session):
    from app.models import Transaction
    import tensorflow as tf
    import keras
    
    # Giới hạn cache
    if len(_model_cache) > 5:
        _model_cache.clear()
        
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    if not transactions or len(transactions) < 10:
        return None
        
    data = [{'date': t.date, 'amount': float(t.amount), 'category': t.category, 'type': t.type} for t in transactions]
    X, y = prepare_data(data, user_id)
    if X is None:
        return None
        
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        keras_model = build_model(X.shape[1])
        keras_model.fit(X_train, y_train, epochs=20, batch_size=16, validation_data=(X_test, y_test), verbose=0)
        
        # --- BẮT ĐẦU QUÁ TRÌNH QUANTIZATION SANG TFLITE ---
        converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
        # Bật tối ưu hóa mặc định (Quantization động - Dynamic Range Quantization)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        tflite_model = converter.convert()
        
        # Lưu file .tflite siêu nhẹ
        with open(_get_paths(user_id)['model'], 'wb') as f:
            f.write(tflite_model)
        # --- KẾT THÚC QUÁ TRÌNH QUANTIZATION ---
        
        # Xóa Keras model khỏi RAM để giải phóng bộ nhớ ngay lập tức
        del keras_model
        tf.keras.backend.clear_session()
        
        return True
    except Exception as e:
        print(f"Lỗi khi train model: {e}")
        return None

def predict_expense(user_id, future_date, category, db_session):
    paths = _get_paths(user_id)
    import tensorflow as tf
    
    # Nếu chưa có model, tiến hành train
    if not os.path.exists(paths['model']):
        train_model(user_id, db_session)
        if not os.path.exists(paths['model']):
            return 0.0
            
    # Load Interpreter từ Cache hoặc từ ổ cứng
    if user_id in _model_cache:
        interpreter = _model_cache[user_id]['interpreter']
        input_details = _model_cache[user_id]['input_details']
        output_details = _model_cache[user_id]['output_details']
        scaler = _model_cache[user_id]['scaler']
        le = _model_cache[user_id]['encoder']
    else:
        try:
            # TFLite Interpreter cực nhẹ, chỉ chiếm vài MB RAM
            interpreter = tf.lite.Interpreter(model_path=paths['model'])
            interpreter.allocate_tensors()
            
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            scaler = joblib.load(paths['scaler'])
            le = joblib.load(paths['encoder'])
            
            _model_cache[user_id] = {
                'interpreter': interpreter,
                'input_details': input_details,
                'output_details': output_details,
                'scaler': scaler,
                'encoder': le
            }
        except Exception as e:
            print(f"Lỗi load TFLite model: {e}")
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
    ]], dtype=np.float32) # TFLite yêu cầu float32 cho input
    
    features_scaled = scaler.transform(features).astype(np.float32)
    
    # --- QUÁ TRÌNH DỰ ĐOÁN BẰNG TFLITE ---
    interpreter.set_tensor(input_details[0]['index'], features_scaled)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])[0][0]
    
    return max(0, float(prediction))