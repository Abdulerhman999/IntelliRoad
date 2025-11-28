from database import get_conn
import json

def fetch_material_id(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT material_id FROM materials WHERE LOWER(material_name)=LOWER(%s)", (name,))
    r = cur.fetchone()
    cur.close()
    conn.close()
    return r["material_id"] if r else None

def insert_project(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tenders (road_length_m, road_width_m, project_type, location_id)
        VALUES (%s,%s,%s,%s)
    """, (
        data["road_length_m"],
        data["road_width_m"],
        data["project_type"],
        data["location_id"]
    ))
    conn.commit()
    tid = cur.lastrowid
    cur.close()
    conn.close()
    return tid

def insert_ml_training_row(tender_id, features_json, materials_json):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ml_training_data (tender_id, features_json, materials_json)
        VALUES (%s,%s,%s)
    """, (tender_id, json.dumps(features_json), json.dumps(materials_json)))
    conn.commit()
    cur.close()
    conn.close()

def insert_prediction(tender_id, cost):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions (tender_id, total_cost)
        VALUES (%s,%s)
    """, (tender_id, cost))
    conn.commit()
    pid = cur.lastrowid
    cur.close()
    conn.close()
    return pid