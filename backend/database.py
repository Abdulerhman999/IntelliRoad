import pymysql
from pymysql.cursors import DictCursor
import yaml

cfg = yaml.safe_load(open("config.yaml"))

def get_conn():
    return pymysql.connect(
        host=cfg["mysql"]["host"],
        user=cfg["mysql"]["user"],
        password=cfg["mysql"]["password"],
        db=cfg["mysql"]["db"],
        cursorclass=DictCursor,
        charset="utf8mb4"
    )

def insert_tender_record(tender):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tenders
        (source_site, tender_url, tender_no, title, department, city, province, 
         publish_date, closing_date, category, procurement_method, opening_date, 
         status, organization, raw_pdf_path, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
    """, (
        tender.get("source_site"),
        tender.get("tender_url"),
        tender.get("tender_no"),
        tender.get("title"),
        tender.get("department"),
        tender.get("city"),
        tender.get("province"),
        tender.get("publish_date"),
        tender.get("closing_date"),
        tender.get("category"),
        tender.get("procurement_method"),
        tender.get("opening_date"),
        tender.get("status"),
        tender.get("organization"),
        tender.get("raw_pdf_path")
    ))
    tid = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return tid

def upsert_material(name, unit):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT material_id FROM materials WHERE LOWER(material_name)=LOWER(%s)", (name,))
    r = cur.fetchone()
    if r:
        mid = r["material_id"]
    else:
        # Note: In new schema materials link to categories, but for scraper/legacy support we allow null category
        cur.execute("INSERT INTO materials (material_name, unit) VALUES (%s,%s)", (name, unit))
        mid = cur.lastrowid
        conn.commit()
    cur.close()
    conn.close()
    return mid

def insert_boq_line(tender_id, boq_id, item_code, description, unit, quantity, rate, cost, raw_line):
    """Insert a parsed BOQ line into the boq_items table."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO boq_items
        (tender_id, boq_id, item_code, description, unit, quantity, rate, cost, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
    """, (tender_id, boq_id, item_code, description, unit, quantity, rate, cost))
    
    conn.commit()
    cur.close()
    conn.close()

def insert_boq_file(tender_id, file_path, extracted_text, db=None):
    """Insert a BOQ file record and return the boq_id."""
    conn = db or get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO boq_files (tender_id, file_path, extracted_text, created_at)
        VALUES (%s, %s, %s, NOW())
    """, (tender_id, file_path, extracted_text))

    boq_id = cur.lastrowid
    conn.commit()

    if not db:
        cur.close()
        conn.close()

    return boq_id

def stage_price_row(material_name, source_name, unit, price_pkr, year, metadata=None, tender_id=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT material_id FROM materials WHERE LOWER(material_name)=LOWER(%s)", (material_name,))
    r = cur.fetchone()
    mat_id = r["material_id"] if r else None
    cur.execute("""
        INSERT INTO material_price_raw
        (material_name, canonical_material_id, source_name, unit, price_pkr, year, metadata, tender_id, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
    """, (material_name, mat_id, source_name, unit, price_pkr, year, yaml.safe_dump(metadata or {}), tender_id))
    conn.commit()
    cur.close()
    conn.close()

# --- WEB UI EXPANSION FUNCTIONS ---

def save_project_full(user_id, input_data, prediction_result, db_boq_list, db_recommendations, features_json, pdf_path):
    """
    Saves the full project state into normalized tables (Projects, BOQ, Impacts).
    """
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # 1. Insert Project Header
        # Calculate area in hectares: (L_km * 1000) * W_m / 10000
        
        cur.execute("""
            INSERT INTO projects 
            (user_id, project_name, location, location_type, company, 
             length_km, width_m, area_hectares, project_type, traffic_volume, 
             soil_type, road_spec_text, max_budget, predicted_cost, 
             budget_status, climate_score, features_json, pdf_path, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id, 
            input_data.project_name, 
            input_data.location, 
            input_data.location_type,
            input_data.parent_company, 
            input_data.road_length_km, 
            input_data.road_width_m,
            (input_data.road_length_km * 1000 * input_data.road_width_m) / 10000.0, 
            input_data.project_type, 
            input_data.traffic_volume, 
            input_data.soil_type,
            prediction_result['spec_text'], 
            input_data.max_budget_pkr, 
            prediction_result['predicted_cost'], 
            'Within Budget' if prediction_result['within_budget'] else 'Over Budget',
            prediction_result['climate_score'], 
            features_json,
            pdf_path
        ))
        project_id = cur.lastrowid

        # 2. Insert BOQ Items (Batch)
        if db_boq_list:
            boq_values = []
            for item in db_boq_list:
                boq_values.append((
                    project_id, item['name'], item['quantity'], item['unit'], 
                    item['price'], item['total'], item['category']
                ))
            
            cur.executemany("""
                INSERT INTO project_boq_estimates 
                (project_id, material_name, quantity, unit, unit_price, total_cost, category_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, boq_values)

        # 3. Insert Recommendations (Batch)
        if db_recommendations:
            rec_values = []
            for rec in db_recommendations:
                rec_values.append((
                    project_id, rec['group'], rec['text'], rec.get('metric', '')
                ))
                
            cur.executemany("""
                INSERT INTO project_impact_reports 
                (project_id, group_name, recommendation_text, specific_metric_value)
                VALUES (%s, %s, %s, %s)
            """, rec_values)

        conn.commit()
        return project_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def get_project_details_full(project_id):
    """Fetches all related data for the web view pages."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Get Header
        cur.execute("SELECT * FROM projects WHERE project_id=%s", (project_id,))
        project = cur.fetchone()
        
        if not project:
            return {"project": None}

        # Get BOQ
        cur.execute("SELECT * FROM project_boq_estimates WHERE project_id=%s", (project_id,))
        boq = cur.fetchall()
        
        # Get Recommendations
        cur.execute("SELECT * FROM project_impact_reports WHERE project_id=%s", (project_id,))
        recs = cur.fetchall()
        
        return { "project": project, "boq": boq, "recommendations": recs }
    finally:
        cur.close()
        conn.close()