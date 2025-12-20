from backend.database import get_conn
import json

def prepare_ml_training_data():
    """
    Build training dataset from structured tenders table.
    Maps database columns directly to ML features for XGBoost.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    print("="*60)
    print("PREPARING ML TRAINING DATA (STRUCTURED VERSION)")
    print("="*60)
    
    # [1/3] Retrieve structured data directly from the new tenders table
    print("\n[1/3] Fetching structured tender features...")
    cur.execute("""
        SELECT 
            tender_id, 
            location_type, 
            road_length_km, 
            road_width_m, 
            project_type, 
            traffic_volume, 
            soil_type, 
            actual_cost_pkr, 
            boq_json 
        FROM tenders 
        WHERE actual_cost_pkr > 0 
        AND used_for_training = TRUE
    """)
    
    tenders = cur.fetchall()
    print(f"[INFO] Found {len(tenders)} tenders available for training.")
    
    if not tenders:
        print("\n[ERROR] No valid training data found in tenders table!")
        cur.close()
        conn.close()
        return

    print("\n[2/3] Processing features for XGBoost...")
    processed = 0
    
    for tender in tenders:
        tid = tender['tender_id']
        
        # Initialize features with direct numerical values
        features = {
            "road_length_km": float(tender['road_length_km']),
            "road_width_m": float(tender['road_width_m']),
            # Categorical features (to be encoded during model training)
            "location_type": tender['location_type'],
            "project_type": tender['project_type'],
            "traffic_volume": tender['traffic_volume'],
            "soil_type": tender['soil_type'],
            # Material aggregates from BOQ
            "cement_qty": 0.0,
            "bitumen_qty": 0.0,
            "steel_qty": 0.0,
            "aggregate_qty": 0.0
        }

        # Parse the BOQ JSON to get precise material quantities
        if tender['boq_json']:
            try:
                boq_items = json.loads(tender['boq_json'])
                for item in boq_items:
                    mat_name = item['material'].lower()
                    qty = float(item['quantity'])
                    
                    if 'cement' in mat_name:
                        features["cement_qty"] += qty
                    elif 'bitumen' in mat_name:
                        features["bitumen_qty"] += qty
                    elif 'steel' in mat_name:
                        features["steel_qty"] += qty
                    elif any(x in mat_name for x in ['stone', 'crush', 'bajri']):
                        features["aggregate_qty"] += qty
            except (json.JSONDecodeError, KeyError, TypeError):
                print(f"    [WARN] Could not parse BOQ JSON for Tender {tid}")

        # Insert into ml_training_data using the new schema columns
        # Note: label_cost_pkr matches your schema.sql
        cur.execute("""
            INSERT INTO ml_training_data (tender_id, features_json, label_cost_pkr, data_quality, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                features_json=VALUES(features_json), 
                label_cost_pkr=VALUES(label_cost_pkr),
                data_quality=VALUES(data_quality),
                created_at=NOW()
        """, (
            tid, 
            json.dumps(features), 
            tender['actual_cost_pkr'],
            'High'  # Structured data is considered High quality
        ))
        
        processed += 1
        if processed % 50 == 0:
            print(f"    Processed {processed} records...")

    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print(f"✅ Prepared {processed} training records in ml_training_data")
    print("="*60)

if __name__ == "__main__":
    prepare_ml_training_data()