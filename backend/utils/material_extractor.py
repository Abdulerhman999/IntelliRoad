import re
from backend.database import get_conn, upsert_material

MATERIAL_KEYWORDS = {
    "cement opc": "Cement OPC Grade 53",
    "cement ppc": "Cement PPC",
    "bitumen 60": "Bitumen 60/70",
    "bitumen 80": "Bitumen 80/100",
    "steel bar": "Steel Bar 10mm",
    "steel mesh": "Steel Mesh",
    "crushed stone": "Crushed Stone 20mm",
    "aggregate": "Crushed Stone 20mm",
    "sand": "Ravi Sand",
    "ravi sand": "Ravi Sand",
    "chenab sand": "Chenab Sand",
    "brick": "Brick Ballast",
    "asphalt": "Asphaltic Concrete",
    "concrete": "Cement OPC Grade 53",
}

def extract_material_prices_from_boq():
    """
    Parse boq_items to identify materials and their prices.
    Store in material_price_raw table for aggregation.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all BOQ items with prices
    cur.execute("""
        SELECT bi.item_id, bi.tender_id, bi.description, bi.unit, bi.rate, bi.quantity, bi.cost,
               t.organization, t.city, t.province, YEAR(t.created_at) as year
        FROM boq_items bi
        JOIN tenders t ON bi.tender_id = t.tender_id
        WHERE bi.rate IS NOT NULL AND bi.rate > 0
    """)
    
    items = cur.fetchall()
    print(f"Processing {len(items)} BOQ items...")
    
    count = 0
    for item in items:
        desc_lower = item['description'].lower()
        
        # Try to match material keywords
        matched_material = None
        for keyword, canonical_name in MATERIAL_KEYWORDS.items():
            if keyword in desc_lower:
                matched_material = canonical_name
                break
        
        if matched_material:
            # Ensure material exists
            mat_id = upsert_material(matched_material, item['unit'] or 'unit')
            
            # Insert into material_price_raw
            cur.execute("""
                INSERT INTO material_price_raw
                (material_name, canonical_material_id, unit, price_pkr, year, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                matched_material,
                mat_id,
                item['unit'] or 'unit',
                item['rate'],
                item['year'] or 2025,
                f"PPRA Tender {item['tender_id']} - {item['organization']}"
            ))
            count += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Extracted {count} material prices")
    return count

if __name__ == "__main__":
    extract_material_prices_from_boq()