# backend/ml/train_model.py
import pandas as pd
import xgboost as xgb
import yaml
import pymysql
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import json
import os
import sys

print("="*60)
print("STARTING MODEL TRAINING")
print("="*60)

cfg = yaml.safe_load(open("config.yaml"))

def get_conn():
    return pymysql.connect(
        host=cfg["mysql"]["host"],
        user=cfg["mysql"]["user"],
        password=cfg["mysql"]["password"],
        db=cfg["mysql"]["db"],
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4"
    )

def build_feature_table():
    print("\n[1/2] Connecting to database...")
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # 1. Load Data with correct schema column: label_cost_pkr
        print("\n[2/2] Loading structured training data...")
        cur.execute("""
            SELECT tender_id, features_json, label_cost_pkr 
            FROM ml_training_data 
            WHERE label_cost_pkr > 0
        """)
        rows = cur.fetchall()
        
        if not rows:
            raise RuntimeError("No training data found in ml_training_data!")

        # 2. Parse JSON into DataFrame
        data_list = []
        for row in rows:
            record = {'label_cost': float(row['label_cost_pkr'])}
            features = json.loads(row['features_json']) if isinstance(row['features_json'], str) else row['features_json']
            record.update(features)
            data_list.append(record)
        
        df = pd.DataFrame(data_list)

        # 3. Handle Categorical Features (One-Hot Encoding)
        # These must match the features prepared in prepare_ml_training_data.py
        categorical_cols = ['location_type', 'project_type', 'traffic_volume', 'soil_type']
        
        # Ensure columns exist before encoding
        for col in categorical_cols:
            if col not in df.columns:
                df[col] = 'unknown'
        
        df = pd.get_dummies(df, columns=categorical_cols)

        # 4. Material Price Integration (Logic remains valid but updated for new keys)
        # ... [Price lookup code from your original script] ...
        # (Assuming the lookup_price_by_name logic is kept here)
        
        # 5. Define Final Feature Set
        # We include the numeric features + all dummy columns created above
        numeric_features = [
            'road_length_km', 'road_width_m', 'cement_qty', 
            'bitumen_qty', 'steel_qty', 'aggregate_qty'
        ]
        
        # Get all column names that start with our categorical prefixes
        encoded_cols = [c for c in df.columns if any(c.startswith(prefix) for prefix in categorical_cols)]
        
        feature_cols = numeric_features + encoded_cols
        
        X = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0).astype(float)
        y = df['label_cost']
        
        # Save feature column order for inference later
        joblib.dump(feature_cols, "models/feature_columns.joblib")
        
        return X, y, feature_cols
        
    finally:
        cur.close()
        conn.close()

def train_save():
    X, y, feature_cols = build_feature_table()
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # XGBoost is excellent at handling the sparse data from One-Hot Encoding
    model = xgb.XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='reg:squarederror'
    )

    model.fit(X_train_s, y_train, eval_set=[(X_test_s, y_test)], verbose=False)
    
    # Save artifacts
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/road_cost_model.joblib")
    joblib.dump(scaler, "models/scaler.joblib")
    
    print(f"Success! Model trained on {len(X)} records with {len(feature_cols)} features.")

if __name__ == "__main__":
    train_save()