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