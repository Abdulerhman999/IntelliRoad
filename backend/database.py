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
    """
    Insert a BOQ file record and return the boq_id.
    """
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
