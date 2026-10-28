import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

# Tắt cảnh báo rác
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'

# Trỏ đường dẫn lưu model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'static', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Bộ nhớ đệm (Cache)
_model_cache = {}

def _get_paths(user_id):
    return {
        # Sử dụng đuôi .tflite cho siêu nhẹ
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

# ==========================================
# KIẾN TRÚC MÔ HÌNH CHO KNOWLEDGE DISTILLATION
# ==========================================

def build_teacher_model(input_dim):
    """Mô hình Giáo viên (Lớn hơn, học sâu hơn)"""
    import keras
    from keras import layers
    
    model = keras.Sequential([
        layers.Dense(64, activation='relu', input_shape=(input_dim,)),
        layers.Dropout(0.2),
        layers.Dense(32, activation='relu'),
        layers.Dense(16, activation='relu'),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def build_student_model(input_dim):
    """Mô hình Học trò (Nhỏ gọn, chạy cực nhanh)"""
    import keras
    from keras import layers
    
    model = keras.Sequential([
        layers.Dense(16, activation='relu', input_shape=(input_dim,)),
        layers.Dense(8, activation='relu'),
        layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

class Distiller:
    """Lớp quản lý quá trình huấn luyện Knowledge Distillation"""
    def __init__(self, student, teacher):
        import tensorflow as tf
        self.teacher = teacher
        self.student = student
        self.student_loss_fn = tf.keras.losses.MeanSquaredError()
        self.distillation_loss_fn = tf.keras.losses.MeanSquaredError()
        self.alpha = 0.3 # Trọng số ưu tiên học từ dữ liệu thực (0.3) và giáo viên (0.7)

    def compile(self, optimizer):
        self.optimizer = optimizer

    def fit(self, X, y, epochs=20, batch_size=16, validation_data=None):
        import tensorflow as tf
        X_tensor = tf.convert_to_tensor(X, dtype=tf.float32)
        y_tensor = tf.convert_to_tensor(y, dtype=tf.float32)
        
        dataset = tf.data.Dataset.from_tensor_slices((X_tensor, y_tensor)).batch(batch_size)
        
        for epoch in range(epochs):
            for x_batch, y_batch in dataset:
                with tf.GradientTape() as tape:
                    # 1. Giáo viên dự đoán (Không cập nhật trọng số giáo viên)
                    teacher_predictions = self.teacher(x_batch, training=False)
                    # 2. Học trò dự đoán
                    student_predictions = self.student(x_batch, training=True)
                    
                    # 3. Tính Loss
                    student_loss = self.student_loss_fn(y_batch, student_predictions)
                    distillation_loss = self.distillation_loss_fn(teacher_predictions, student_predictions)
                    
                    # 4. Tổng hợp Loss
                    loss = self.alpha * student_loss + (1 - self.alpha) * distillation_loss
                
                # Cập nhật trọng số Học trò
                trainable_vars = self.student.trainable_variables
                gradients = tape.gradient(loss, trainable_vars)
                self.optimizer.apply_gradients(zip(gradients, trainable_vars))
                
        print(f"Hoàn thành huấn luyện Distillation. Loss cuối: {loss.numpy():.4f}")

# ==========================================
# HUẤN LUYỆN VÀ DỰ ĐOÁN
# ==========================================

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
        
        # 1. Huấn luyện Giáo viên
        teacher = build_teacher_model(X.shape[1])
        teacher.fit(X_train, y_train, epochs=30, batch_size=16, verbose=0)
        
        # 2. Khởi tạo Học trò
        student = build_student_model(X.shape[1])
        
        # 3. Chưng cất tri thức (Distillation)
        distiller = Distiller(student=student, teacher=teacher)
        distiller.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001))
        distiller.fit(X_train, y_train, epochs=20, batch_size=16)
        
        # 4. Chuyển đổi Học trò sang TFLite (Quantization)
        converter = tf.lite.TFLiteConverter.from_keras_model(student)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        
        # Lưu file .tflite siêu nhẹ
        with open(_get_paths(user_id)['model'], 'wb') as f:
            f.write(tflite_model)
        
        # Giải phóng bộ nhớ
        del teacher, student, distiller
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
    ]], dtype=np.float32)
    
    features_scaled = scaler.transform(features).astype(np.float32)
    
    # --- QUÁ TRÌNH DỰ ĐOÁN BẰNG TFLITE ---
    interpreter.set_tensor(input_details[0]['index'], features_scaled)
    interpreter.invoke()
    prediction = interpreter.get_tensor(output_details[0]['index'])[0][0]
    
    return max(0, float(prediction))