# backend/ml/diagnose_ml_data.py
import yaml
import pymysql
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

print("="*60)
print("DIAGNOSING ML TRAINING DATA")
print("="*60)

conn = get_conn()
cur = conn.cursor()

# Check table structure
print("\n[1] Checking table structure...")
cur.execute("DESCRIBE ml_training_data")
columns = cur.fetchall()
print("Columns:")
for col in columns:
    print(f"  - {col['Field']}: {col['Type']}")

# Check row count
print("\n[2] Checking row count...")
cur.execute("SELECT COUNT(*) as count FROM ml_training_data")
count = cur.fetchone()
print(f"Total rows: {count['count']}")

# Check sample data
print("\n[3] Checking first 3 rows...")
cur.execute("SELECT * FROM ml_training_data LIMIT 3")
rows = cur.fetchall()

for i, row in enumerate(rows, 1):
    print(f"\n--- Row {i} ---")
    print(f"training_id: {row['training_id']}")
    print(f"tender_id: {row['tender_id']}")
    print(f"label_cost: {row['label_cost']} (type: {type(row['label_cost'])})")
    print(f"features_json (raw): {row['features_json'][:200] if row['features_json'] else 'NULL'}...")
    
    # Try to parse features_json
    if row['features_json']:
        try:
            features = json.loads(row['features_json'])
            print(f"features_json (parsed): {features}")
            print(f"features_json keys: {list(features.keys()) if isinstance(features, dict) else 'Not a dict'}")
        except Exception as e:
            print(f"ERROR parsing features_json: {e}")
            # Try alternate parsing
            try:
                features = json.loads(row['features_json'].replace("'", '"'))
                print(f"features_json (parsed with quote fix): {features}")
            except Exception as e2:
                print(f"ERROR with quote fix too: {e2}")

# Check for valid training data
print("\n[4] Checking valid training data...")
cur.execute("""
    SELECT COUNT(*) as count 
    FROM ml_training_data 
    WHERE label_cost IS NOT NULL AND label_cost > 0
""")
valid = cur.fetchone()
print(f"Rows with valid label_cost (NOT NULL and > 0): {valid['count']}")

# Check label_cost statistics
print("\n[5] Checking label_cost statistics...")
cur.execute("""
    SELECT 
        MIN(label_cost) as min_cost,
        MAX(label_cost) as max_cost,
        AVG(label_cost) as avg_cost
    FROM ml_training_data
    WHERE label_cost IS NOT NULL AND label_cost > 0
""")
stats = cur.fetchone()
if stats['min_cost']:
    print(f"Min cost: {stats['min_cost']:,.2f}")
    print(f"Max cost: {stats['max_cost']:,.2f}")
    print(f"Avg cost: {stats['avg_cost']:,.2f}")
else:
    print("No valid cost data found!")

cur.close()
conn.close()

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)