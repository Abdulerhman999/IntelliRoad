from backend.scrapers.ppra_scraper import run_ppra_org
from backend.utils.material_extractor import extract_materials_from_boq_items
from backend.utils.price_processor import recompute_all
from backend.database import get_conn

def run_full_pipeline():
    print("="*60)
    print("STEP 1: Scraping PPRA tenders...")
    print("="*60)
    run_ppra_org(org_id=38, debug=False, headless=True)
    
    print("\n" + "="*60)
    print("STEP 2: Extracting material prices from BOQ items...")
    print("="*60)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT tender_id FROM tenders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)")
    recent_tenders = cur.fetchall()
    cur.close()
    conn.close()
    
    for row in recent_tenders:
        tid = row["tender_id"]
        count = extract_materials_from_boq_items(tid, year=2025)
        print(f"  Extracted {count} material prices from tender {tid}")
    
    print("\n" + "="*60)
    print("STEP 3: Aggregating yearly prices...")
    print("="*60)
    recompute_all(years=[2023, 2024, 2025])
    
    print("\n" + "="*60)
    print("STEP 4: Ready for ML training!")
    print("="*60)
    print("Run: python -m backend.ml.train_model")

if __name__ == "__main__":
    run_full_pipeline()