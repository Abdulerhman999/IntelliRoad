import fitz
import re
from backend.database import upsert_material, insert_boq_line, stage_price_row, insert_boq_file

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    parts = []
    for i in range(len(doc)):
        parts.append(doc[i].get_text("text"))
    return "\n".join(parts)

def parse_money(s):
    if not s:
        return None
    s = re.sub(r"[^\d\.]", "", s)
    try:
        return float(s)
    except:
        return None

def parse_boq_lines_from_text(text):
    lines = text.splitlines()
    candidates = []

    pattern = re.compile(
        r"^\s*(\d+[\.\d\-]*)\s+(.{10,200}?)\s+([0-9,\.]+)\s*(m3|m2|mt|ton|tonne|kg|cft|rm|ft2|ft|bag|nos)?\s+([Rs\.\s0-9,\.]+)\s+([Rs\.\s0-9,\.]+)",
        re.IGNORECASE,
    )

    for ln in lines:
        m = pattern.search(ln)
        if m:
            item_no = m.group(1).strip()
            desc = m.group(2).strip()
            qty = float(m.group(3).replace(",", ""))
            unit = (m.group(4) or "").strip()
            unit_price = parse_money(m.group(5))
            total_price = parse_money(m.group(6))
            candidates.append(
                {
                    "item_no": item_no,
                    "description": desc,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "raw": ln,
                }
            )

    if not candidates:
        loose = re.compile(
            r"(.{10,80}?)\s+([0-9,\.]+)\s+(m3|mt|kg|cft|bag|rm|m2|ft2)?\s+([Rs\.\s0-9,\.]+)",
            re.IGNORECASE,
        )
        for ln in lines:
            m = loose.search(ln)
            if m:
                desc = m.group(1).strip()
                qty = float(m.group(2).replace(",", ""))
                unit = (m.group(3) or "").strip()
                unit_price = parse_money(m.group(4))
                total_price = qty * unit_price if unit_price else None
                candidates.append(
                    {
                        "item_no": None,
                        "description": desc,
                        "unit": unit,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total_price": total_price,
                        "raw": ln,
                    }
                )

    return candidates

def parse_and_store_boq(tender_id, pdf_path, db=None):
    """
    1. Extract text from PDF
    2. Insert BOQ file record
    3. Parse BOQ line items
    4. Insert parsed BOQ lines
    """

    # 1. Extract text
    text = extract_text_from_pdf(pdf_path)

    # 2. Insert the file record
    boq_id = insert_boq_file(
        tender_id=tender_id,
        file_path=pdf_path,
        extracted_text=text,
        db=db
    )

    # 3. Parse items
    items = parse_boq_lines_from_text(text)

    # 4. Insert each BOQ item
    for it in items:
        insert_boq_line(
            tender_id=tender_id,
            boq_id=boq_id,
            item_code=it["item_no"],
            description=it["description"],
            unit=it["unit"],
            quantity=it["quantity"],
            rate=it["unit_price"],
            cost=it["total_price"],
            raw_line=it["raw"],
            db=db
        )

    return boq_id