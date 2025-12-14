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
    print("\n[1/5] Connecting to database...")
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Check if ml_training_data table exists and has data
        cur.execute("SELECT COUNT(*) as count FROM ml_training_data")
        result = cur.fetchone()
        record_count = result['count']
        
        print(f"[INFO] Found {record_count} records in ml_training_data table")
        
        if record_count == 0:
            print("\n[ERROR] No training data found!")
            print("You need to run: python -m backend.ml.prepare_ml_training_data")
            print("OR populate ml_training_data table first")
            sys.exit(1)
        
        # Get training data using cursor instead of pd.read_sql
        print("\n[2/5] Loading training data...")
        cur.execute("""
            SELECT tender_id, features_json, label_cost
            FROM ml_training_data
            WHERE label_cost IS NOT NULL AND label_cost > 0
        """)
        
        rows = cur.fetchall()
        
        if not rows:
            raise RuntimeError("No valid training data found (all label_cost are NULL or 0)")
        
        print(f"[INFO] Loaded {len(rows)} training records")

        # Parse features_json and build DataFrame manually
        print("\n[3/5] Parsing features...")
        
        data_list = []
        for row in rows:
            # Get basic fields
            record = {
                'tender_id': row['tender_id'],
                'label_cost': float(row['label_cost'])
            }
            
            # Parse features_json
            features_json = row['features_json']
            if isinstance(features_json, str):
                try:
                    features = json.loads(features_json)
                except:
                    features = {}
            elif isinstance(features_json, dict):
                features = features_json
            else:
                features = {}
            
            # Add all features to the record
            record.update(features)
            data_list.append(record)
        
        # Create DataFrame from list of dictionaries
        df = pd.DataFrame(data_list)
        
        print(f"[DEBUG] DataFrame shape: {df.shape}")
        print(f"[DEBUG] DataFrame columns: {df.columns.tolist()}")
        print(f"[DEBUG] First label_cost values: {df['label_cost'].head().tolist()}")

        # Get material prices from database
        print("\n[4/5] Loading material prices...")
        cur.execute("SELECT material_id, LOWER(material_name) AS material_name FROM materials")
        mats = cur.fetchall()
        material_name_to_id = {r["material_name"]: r["material_id"] for r in mats}
        
        print(f"[INFO] Found {len(material_name_to_id)} materials in database")

        # Get price history
        cur.execute("""
            SELECT material_id, year, price_pkr
            FROM material_price_history
            WHERE year IN (2023, 2024, 2025)
        """)
        price_rows = cur.fetchall()
        
        print(f"[INFO] Found {len(price_rows)} price records")

        # Build price lookup
        price_lookup = {}
        for r in price_rows:
            price_lookup[(r["material_id"], int(r["year"]))] = float(r["price_pkr"])

        def lookup_price_by_name(name, year):
            mid = material_name_to_id.get(name.lower())
            if not mid:
                return None
            return price_lookup.get((mid, int(year)), None)

        # Add prices to dataframe - handle missing 'year' column
        if "year" in df.columns:
            years = df["year"].fillna(2025).astype(int)
        else:
            years = pd.Series([2025] * len(df))
        
        print(f"[DEBUG] Years shape: {years.shape}")
        
        df["cement_price"] = [lookup_price_by_name("cement opc grade 53", y) or 1550 for y in years]
        df["bitumen_price"] = [lookup_price_by_name("bitumen 60/70", y) or 175000 for y in years]
        df["steel_price"] = [lookup_price_by_name("steel bar 10mm", y) or 255 for y in years]

        # Prepare features - ensure columns exist
        for col in ["cement_qty_ton", "bitumen_qty_ton", "steel_qty_ton", "road_length_km", "road_width_km"]:
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Calculate material costs
        df["cement_cost"] = df["cement_qty_ton"] * df["cement_price"]
        df["bitumen_cost"] = df["bitumen_qty_ton"] * df["bitumen_price"]
        df["steel_cost"] = df["steel_qty_ton"] * df["steel_price"]
        df["materials_total"] = df["cement_cost"] + df["bitumen_cost"] + df["steel_cost"]

        # Feature columns (must match inference.py FEATURE_ORDER)
        feature_cols = [
            "road_length_km",
            "road_width_km",
            "cement_qty_ton",
            "bitumen_qty_ton",
            "steel_qty_ton",
            "cement_price",
            "bitumen_price",
            "steel_price",
            "materials_total",
        ]
        
        # Ensure all feature columns exist
        for col in feature_cols:
            if col not in df.columns:
                print(f"[WARNING] Missing feature column: {col}, setting to 0")
                df[col] = 0.0
        
        # Convert to numeric and fill NaN
        X = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0).astype(float)
        y = pd.to_numeric(df["label_cost"], errors='coerce').astype(float)
        
        # Remove any rows where y is 0 or NaN (invalid training data)
        valid_mask = (y > 0) & (~y.isna())
        X = X[valid_mask]
        y = y[valid_mask]
        
        print(f"\n[INFO] Feature matrix shape: {X.shape}")
        print(f"[INFO] Target vector shape: {y.shape}")
        print(f"[INFO] Feature columns: {feature_cols}")
        print(f"[DEBUG] Sample X values:\n{X.head()}")
        print(f"[DEBUG] Sample y values: {y.head().tolist()}")
        
        if len(X) == 0:
            raise RuntimeError("No valid training data after filtering!")
        
        return X, y
        
    finally:
        cur.close()
        conn.close()

def train_save():
    try:
        print("\n" + "="*60)
        print("BUILDING FEATURE TABLE")
        print("="*60)
        
        X, y = build_feature_table()
        
        print("\n" + "="*60)
        print("TRAINING MODEL")
        print("="*60)
        
        print("\n[5/5] Splitting data and training...")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        print(f"[INFO] Training set: {X_train.shape[0]} samples")
        print(f"[INFO] Test set: {X_test.shape[0]} samples")
        
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = xgb.XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=1,
        )

        print("\n[INFO] Training XGBoost model...")
        model.fit(
            X_train_s,
            y_train,
            eval_set=[(X_test_s, y_test)],
            verbose=True,
        )

        # Save model and scaler
        model_path = cfg["training"].get("model_path", "models/road_cost_predictor.joblib")
        scaler_path = cfg["training"].get("scaler_path", "models/scaler.joblib")
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        print(f"\n[INFO] Saving model to {model_path}")
        joblib.dump(model, model_path)
        
        print(f"[INFO] Saving scaler to {scaler_path}")
        joblib.dump(scaler, scaler_path)

        # Test prediction
        print("\n[INFO] Testing model with sample prediction...")
        sample_pred = model.predict(X_test_s[:1])
        print(f"[INFO] Sample prediction: {sample_pred[0]:,.2f}")
        print(f"[INFO] Actual value: {y_test.iloc[0]:,.2f}")
        
        # Calculate accuracy metrics
        from sklearn.metrics import mean_absolute_error, r2_score
        train_pred = model.predict(X_train_s)
        test_pred = model.predict(X_test_s)
        
        train_mae = mean_absolute_error(y_train, train_pred)
        test_mae = mean_absolute_error(y_test, test_pred)
        train_r2 = r2_score(y_train, train_pred)
        test_r2 = r2_score(y_test, test_pred)

        print("\n" + "="*60)
        print("MODEL TRAINING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Model saved: {model_path}")
        print(f"Scaler saved: {scaler_path}")
        print(f"Training samples: {X_train.shape[0]}")
        print(f"Test samples: {X_test.shape[0]}")
        print(f"\nModel Performance:")
        print(f"  Train MAE: PKR {train_mae:,.2f}")
        print(f"  Test MAE:  PKR {test_mae:,.2f}")
        print(f"  Train R²:  {train_r2:.4f}")
        print(f"  Test R²:   {test_r2:.4f}")
        print("="*60)

    except Exception as e:
        print("\n" + "="*60)
        print("MODEL TRAINING FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    train_save()