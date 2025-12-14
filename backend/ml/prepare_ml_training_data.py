from backend.database import get_conn
import json
import re

def prepare_ml_training_data():
    """
    Build training dataset from tenders with BOQ items.
    Calculate features and labels for ML model.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    print("="*60)
    print("PREPARING ML TRAINING DATA")
    print("="*60)
    
    # Get tenders with BOQ items
    print("\n[1/3] Finding tenders with BOQ data...")
    cur.execute("""
        SELECT t.tender_id, t.title, t.organization, 
               YEAR(t.created_at) as year,
               SUM(bi.cost) as total_cost,
               COUNT(bi.item_id) as item_count
        FROM tenders t
        JOIN boq_items bi ON t.tender_id = bi.tender_id
        WHERE bi.cost IS NOT NULL AND bi.cost > 0
        GROUP BY t.tender_id
        HAVING total_cost > 0
    """)
    
    tenders = cur.fetchall()
    print(f"[INFO] Found {len(tenders)} tenders with BOQ data")
    
    if len(tenders) == 0:
        print("\n[ERROR] No tenders with BOQ items found!")
        print("Make sure you have run the scraper and it has extracted BOQ items.")
        cur.close()
        conn.close()
        return
    
    print("\n[2/3] Processing each tender...")
    processed = 0
    
    for tender in tenders:
        tid = tender['tender_id']
        year = tender['year'] or 2025
        total_cost = tender['total_cost']
        
        print(f"\n  Processing tender {tid}: {tender['title'][:50]}...")
        
        # Extract features from BOQ items
        cur.execute("""
            SELECT description, unit, quantity, rate, cost
            FROM boq_items
            WHERE tender_id = %s
        """, (tid,))
        
        items = cur.fetchall()
        
        # Initialize feature dict
        features = {
            "road_length_km": 0.0,
            "road_width_km": 0.0,
            "cement_qty_ton": 0.0,
            "bitumen_qty_ton": 0.0,
            "steel_qty_ton": 0.0,
            "aggregate_qty_ton": 0.0,
            "sand_qty_ton": 0.0,
            "year": year
        }
        
        # Extract quantities from items
        for item in items:
            desc = item['description'].lower() if item['description'] else ''
            qty = item['quantity'] or 0
            unit = (item['unit'] or '').lower()
            
            # Estimate road dimensions from description
            km_match = re.search(r'(\d+\.?\d*)\s*km', desc)
            if km_match:
                features["road_length_km"] = max(features["road_length_km"], float(km_match.group(1)))
            
            width_match = re.search(r'(\d+\.?\d*)\s*m.*width', desc)
            if width_match:
                features["road_width_km"] = max(features["road_width_km"], float(width_match.group(1)) / 1000)
            
            # Aggregate material quantities
            if 'cement' in desc:
                if 'bag' in unit:
                    qty_ton = qty * 0.05  # 50kg bag
                elif 'ton' in unit or 'mt' in unit:
                    qty_ton = qty
                else:
                    qty_ton = qty * 0.001  # assume kg
                features["cement_qty_ton"] += qty_ton
            
            if 'bitumen' in desc:
                if 'ton' in unit or 'mt' in unit:
                    features["bitumen_qty_ton"] += qty
                else:
                    features["bitumen_qty_ton"] += qty * 0.001
            
            if 'steel' in desc:
                if 'ton' in unit or 'mt' in unit:
                    features["steel_qty_ton"] += qty
                elif 'kg' in unit:
                    features["steel_qty_ton"] += qty * 0.001
                else:
                    features["steel_qty_ton"] += qty * 0.001
            
            if 'aggregate' in desc or 'crush' in desc or 'stone' in desc:
                features["aggregate_qty_ton"] += qty * 0.04  # rough conversion from cft
            
            if 'sand' in desc:
                features["sand_qty_ton"] += qty * 0.035
        
        # If no road dimensions found, estimate from title
        if features["road_length_km"] == 0:
            title = tender['title'].lower() if tender['title'] else ''
            km_match = re.search(r'(\d+\.?\d*)\s*km', title)
            if km_match:
                features["road_length_km"] = float(km_match.group(1))
        
        print(f"    Length: {features['road_length_km']:.2f} km")
        print(f"    Cement: {features['cement_qty_ton']:.2f} tons")
        print(f"    Bitumen: {features['bitumen_qty_ton']:.2f} tons")
        print(f"    Steel: {features['steel_qty_ton']:.2f} tons")
        print(f"    Total Cost: PKR {total_cost:,.2f}")
        
        # Insert into ml_training_data table
        cur.execute("""
            INSERT INTO ml_training_data (tender_id, features_json, label_cost, created_at)
            VALUES (%s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
                features_json=VALUES(features_json), 
                label_cost=VALUES(label_cost),
                created_at=NOW()
        """, (tid, json.dumps(features), total_cost))
        
        processed += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n" + "="*60)
    print(f"✅ Prepared {processed} training records")
    print("="*60)
    print("\nNow you can train the model by running:")
    print("  python -m backend.ml.train_model")
    print("="*60)

if __name__ == "__main__":
    prepare_ml_training_data()