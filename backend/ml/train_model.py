# backend/ml/train_model.py
import pandas as pd
import xgboost as xgb
import yaml
import pymysql
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import json

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
    conn = get_conn()
    try:
        # join ml_training_data + tenders; bring features_json and year into df
        query = """
        SELECT mld.*, t.road_length_km, t.road_width_km, t.project_type, t.location, t.year
        FROM ml_training_data mld
        JOIN tenders t ON mld.tender_id = t.tender_id
        """
        df = pd.read_sql(query, conn)
        if df.empty:
            raise RuntimeError("No ML training rows found")

        # safe parse features_json column (assume JSON string or dict)
        def safe_load(s):
            if pd.isna(s):
                return {}
            if isinstance(s, dict):
                return s
            try:
                return json.loads(s)
            except Exception:
                # try fallback: replace single quotes -> double quotes (best-effort), else empty
                try:
                    return json.loads(s.replace("'", '"'))
                except Exception:
                    return {}

        features_df = df["features_json"].apply(lambda x: pd.Series(safe_load(x)))
        df = pd.concat([df.reset_index(drop=True), features_df.reset_index(drop=True)], axis=1)

        # Prepare list of years from df
        years = df.get("year", pd.Series([2025] * len(df))).fillna(2025).astype(int)

        # Preload materials mapping and price history in single queries to avoid N*N DB calls
        with conn.cursor() as cur:
            cur.execute("SELECT material_id, LOWER(material_name) AS material_name FROM materials")
            mats = cur.fetchall()
            material_name_to_id = {r["material_name"]: r["material_id"] for r in mats}

            # build list of material ids we'll need (common ones)
            needed_materials = [
                material_name_to_id.get("cement opc grade 53"),
                material_name_to_id.get("bitumen 60/70"),
                material_name_to_id.get("steel bar 10mm"),
                material_name_to_id.get("crushed stone 20mm"),
                material_name_to_id.get("ravi sand"),
            ]
            needed_materials = [mid for mid in needed_materials if mid]

            # get all relevant price rows for years present in dataset
            unique_years = sorted(years.unique().tolist())
            if needed_materials and unique_years:
                fmt_ids = ",".join(["%s"] * len(needed_materials))
                fmt_years = ",".join(["%s"] * len(unique_years))
                sql = f"""
                    SELECT material_id, year, price_pkr
                    FROM material_price_history
                    WHERE material_id IN ({fmt_ids})
                      AND year IN ({fmt_years})
                """
                params = tuple(needed_materials + unique_years)
                cur.execute(sql, params)
                price_rows = cur.fetchall()
            else:
                price_rows = []

        # build lookup dict: (material_id, year) -> price
        price_lookup = {}
        for r in price_rows:
            price_lookup[(r["material_id"], int(r["year"]))] = float(r["price_pkr"])

        # helper to get price by name & year
        def lookup_price_by_name(name, year):
            mid = material_name_to_id.get(name.lower())
            if not mid:
                return None
            return price_lookup.get((mid, int(year)), None)

        # compute price columns
        df["cement_price"] = [lookup_price_by_name("Cement OPC Grade 53", y) for y in years]
        df["bitumen_price"] = [lookup_price_by_name("Bitumen 60/70", y) for y in years]
        df["steel_price"] = [lookup_price_by_name("Steel Bar 10mm", y) for y in years]
        df["aggregate_price"] = [lookup_price_by_name("Crushed Stone 20mm", y) for y in years]
        df["sand_price"] = [lookup_price_by_name("Ravi Sand", y) for y in years]

        # compute material cost features safely
        df["cement_qty_ton"] = df.get("cement_qty_ton", 0).fillna(0)
        df["bitumen_qty_ton"] = df.get("bitumen_qty_ton", 0).fillna(0)
        df["steel_qty_ton"] = df.get("steel_qty_ton", 0).fillna(0)
        df["aggregate_qty_ton"] = df.get("aggregate_qty_ton", 0).fillna(0)
        df["sand_qty_ton"] = df.get("sand_qty_ton", 0).fillna(0)

        df["cement_cost"] = df["cement_qty_ton"] * df["cement_price"].fillna(0)
        df["bitumen_cost"] = df["bitumen_qty_ton"] * df["bitumen_price"].fillna(0)
        df["steel_cost"] = df["steel_qty_ton"] * df["steel_price"].fillna(0)
        df["aggregate_cost"] = df["aggregate_qty_ton"] * df["aggregate_price"].fillna(0)
        df["sand_cost"] = df["sand_qty_ton"] * df["sand_price"].fillna(0)

        # materials total should include all relevant material costs
        df["materials_total"] = df[["cement_cost", "bitumen_cost", "steel_cost", "aggregate_cost", "sand_cost"]].sum(axis=1)

        # X and y (feature set must match inference FEATURE_ORDER)
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
        X = df[feature_cols].fillna(0)
        y = df["label_cost"] if "label_cost" in df.columns else df.get("optimal_total_cost_pkr")
        if y is None:
            raise RuntimeError("No label column (label_cost or optimal_total_cost_pkr) found in ml_training_data")

        return X, y
    finally:
        conn.close()

def train_save():
    X, y = build_feature_table()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
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

    model.fit(
        X_train_s,
        y_train,
        eval_set=[(X_test_s, y_test)],
        early_stopping_rounds=25,
        verbose=True,
    )

    # atomic write: save to temp then move
    model_path = cfg["training"].get("model_path", "models/road_cost_predictor.joblib")
    scaler_path = cfg["training"].get("scaler_path", "models/scaler.joblib")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    # Optionally also save xgboost native booster (JSON) for portability
    try:
        booster_json_path = cfg["training"].get("booster_json_path")
        if booster_json_path:
            model.get_booster().save_model(booster_json_path)
    except Exception:
        pass

    print("Model and scaler saved:", model_path, scaler_path)
