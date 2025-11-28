import joblib
import numpy as np
import yaml
import os

cfg = yaml.safe_load(open("config.yaml"))

MODEL_PATH = cfg["training"].get("model_path", "models/road_cost_predictor.joblib")
SCALER_PATH = cfg["training"].get("scaler_path", "models/scaler.joblib")

# must match training feature_cols order
FEATURE_ORDER = [
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

if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(f"Model or scaler not found. Expected {MODEL_PATH} and {SCALER_PATH}")

_model = joblib.load(MODEL_PATH)
_scaler = joblib.load(SCALER_PATH)

def _validate_and_build_vector(features: dict):
    missing = [f for f in FEATURE_ORDER if f not in features]
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    # enforce ordering and convert to float
    x = [float(features[f]) if features[f] is not None else 0.0 for f in FEATURE_ORDER]
    return np.array([x], dtype=float)

def predict_cost(features: dict):
    """
    features: dict containing exactly the keys in FEATURE_ORDER (extra keys allowed)
    returns: numeric prediction
    """
    x = _validate_and_build_vector(features)
    x_s = _scaler.transform(x)
    pred = _model.predict(x_s)
    return float(pred[0])
    