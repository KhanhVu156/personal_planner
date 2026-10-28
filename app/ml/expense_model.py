import os
import gc # ✅ Thêm thư viện GC để dọn RAM
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib

# ✅ TỐI ƯU RAM: Tắt oneDNN và giới hạn luồng xử lý
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'static', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

_model_cache = {}

def _get_paths(user_id):
    return {
        'model': os.path.join(MODEL_DIR, f'expense_model_{user_id}.tflite'), 
        'scaler': os.path.join(MODEL_DIR, f'scaler_{user_id}.pkl'),
        'encoder': os.path.join(MODEL_DIR, f'encoder_{user_id}.pkl'),
        'target_scaler': os.path.join(MODEL_DIR, f'target_scaler_{user_id}.pkl')
    }

def prepare_data(transactions, user_id):
    df = pd.DataFrame(transactions)
    df = df[df['type'] == 'expense'].copy()
    if df.empty:
        print("[AI Debug] Không có giao dịch chi tiêu (expense) nào để train.")
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
    y = df['amount'].values.reshape(-1, 1) # Reshape cho Scaler
    
    # Scale X
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # ✅ FIX: Scale y (Đưa số tiền về 0-1)
    y_scaler = MinMaxScaler(feature_range=(0, 1))
    y_scaled = y_scaler.fit_transform(y).flatten()
    
    paths = _get_paths(user_id)
    joblib.dump(scaler, paths['scaler'])
    joblib.dump(le, paths['encoder'])
    joblib.dump(y_scaler, paths['target_scaler'])
    
    return X_scaled, y_scaled

def build_teacher_model(input_dim):
    import keras
    from keras import layers
    # ✅ TỐI ƯU: Giảm kích thước mô hình để tiết kiệm RAM
    model = keras.Sequential([
        layers.Dense(32, activation='relu', input_shape=(input_dim,)),
        layers.Dropout(0.2),
        layers.Dense(16, activation='relu'),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def build_student_model(input_dim):
    import keras
    from keras import layers
    # ✅ TỐI ƯU: Giảm kích thước mô hình để tiết kiệm RAM
    model = keras.Sequential([
        layers.Dense(8, activation='relu', input_shape=(input_dim,)),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

class Distiller:
    def __init__(self, student, teacher):
        import tensorflow as tf
        self.teacher = teacher
        self.student = student
        self.student_loss_fn = tf.keras.losses.MeanSquaredError()
        self.distillation_loss_fn = tf.keras.losses.MeanSquaredError()
        self.alpha = 0.3 

    def compile(self, optimizer):
        self.optimizer = optimizer

    def fit(self, X, y, epochs=10, batch_size=16, validation_data=None):
        import tensorflow as tf
        X_tensor = tf.convert_to_tensor(X, dtype=tf.float32)
        y_tensor = tf.convert_to_tensor(y, dtype=tf.float32)
        dataset = tf.data.Dataset.from_tensor_slices((X_tensor, y_tensor)).batch(batch_size)
        
        for epoch in range(epochs):
            for x_batch, y_batch in dataset:
                with tf.GradientTape() as tape:
                    teacher_predictions = self.teacher(x_batch, training=False)
                    student_predictions = self.student(x_batch, training=True)
                    student_loss = self.student_loss_fn(y_batch, student_predictions)
                    distillation_loss = self.distillation_loss_fn(teacher_predictions, student_predictions)
                    loss = self.alpha * student_loss + (1 - self.alpha) * distillation_loss
                
                trainable_vars = self.student.trainable_variables
                gradients = tape.gradient(loss, trainable_vars)
                self.optimizer.apply_gradients(zip(gradients, trainable_vars))
                
        print(f"[AI Debug] Hoàn thành Distillation. Loss cuối: {loss.numpy():.4f}")

def train_model(user_id, db_session):
    from app.models import Transaction
    import tensorflow as tf
    import keras
    
    if len(_model_cache) > 5:
        _model_cache.clear()
        
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).limit(2000).all()
    
    if not transactions or len(transactions) < 10:
        print(f"[AI Debug] User {user_id} chưa đủ 10 giao dịch (chỉ có {len(transactions) if transactions else 0}).")
        return None
        
    data = [{'date': t.date, 'amount': float(t.amount), 'category': t.category, 'type': t.type} for t in transactions]
    X, y = prepare_data(data, user_id)
    if X is None:
        return None
        
    try:
        print(f"[AI Debug] Bắt đầu train cho User {user_id} với {len(X)} dòng dữ liệu...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        teacher = build_teacher_model(X.shape[1])
        # ✅ TỐI ƯU: Giảm epochs từ 30 xuống 15
        teacher.fit(X_train, y_train, epochs=15, batch_size=16, verbose=0)
        
        student = build_student_model(X.shape[1])
        
        distiller = Distiller(student=student, teacher=teacher)
        distiller.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001))
        distiller.fit(X_train, y_train, epochs=10, batch_size=16)
        
        converter = tf.lite.TFLiteConverter.from_keras_model(student)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        
        with open(_get_paths(user_id)['model'], 'wb') as f:
            f.write(tflite_model)
        
        del teacher, student, distiller
        tf.keras.backend.clear_session()
        gc.collect()
        
        print(f"[AI Debug] Train thành công và đã lưu model!")
        return True
    except Exception as e:
        print(f"[AI Debug] Lỗi khi train model: {e}")
        # ✅ Dọn dẹp file rác nếu train thất bại
        for p in _get_paths(user_id).values():
            if os.path.exists(p):
                os.remove(p)
        return None

def predict_expense(user_id, future_date, category, db_session):
    paths = _get_paths(user_id)
    import tensorflow as tf
    
    if not all(os.path.exists(p) for p in paths.values()):
        return 0.0
            
    if user_id in _model_cache:
        interpreter = _model_cache[user_id]['interpreter']
        input_details = _model_cache[user_id]['input_details']
        output_details = _model_cache[user_id]['output_details']
        scaler = _model_cache[user_id]['scaler']
        le = _model_cache[user_id]['encoder']
        y_scaler = _model_cache[user_id]['y_scaler'] 
    else:
        try:
            interpreter = tf.lite.Interpreter(model_path=paths['model'])
            interpreter.allocate_tensors()
            
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            scaler = joblib.load(paths['scaler'])
            le = joblib.load(paths['encoder'])
            y_scaler = joblib.load(paths['target_scaler'])
            
            _model_cache[user_id] = {
                'interpreter': interpreter,
                'input_details': input_details,
                'output_details': output_details,
                'scaler': scaler,
                'encoder': le,
                'y_scaler': y_scaler
            }
        except Exception as e:
            print(f"[AI Debug] Lỗi load TFLite model: {e}")
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
    ]], dtype=np.float32)
    
    features_scaled = scaler.transform(features).astype(np.float32)
    
    interpreter.set_tensor(input_details[0]['index'], features_scaled)
    interpreter.invoke()
    prediction_scaled = interpreter.get_tensor(output_details[0]['index'])[0][0]
    
    prediction = y_scaler.inverse_transform([[prediction_scaled]])[0][0]
    
    return max(0, float(prediction))