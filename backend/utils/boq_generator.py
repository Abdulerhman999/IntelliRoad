from backend.database import get_conn

def fetch_material_price(material_id, year):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT avg_price
        FROM material_price_history
        WHERE material_id=%s AND year=%s
        """,
        (material_id, year),
    )
    r = cur.fetchone()
    cur.close()
    conn.close()
    return float(r["avg_price"]) if r else None

def generate_boq(length, width, year):
    area = length * width
    materials = {
        "Cement OPC Grade 53": 0.12 * area,
        "Steel Bar 10mm": 2.5 * area,
        "Bitumen 60/70": 0.05 * area,
    }

    conn = get_conn()
    cur = conn.cursor()
    boq_lines = []

    for name, qty in materials.items():
        cur.execute("SELECT material_id FROM materials WHERE material_name=%s", (name,))
        m = cur.fetchone()
        if not m:
            continue
        mid = m["material_id"]
        price = fetch_material_price(mid, year)
        if price is None:
            continue
        total = price * qty
        boq_lines.append(f"{name}: {qty:.2f} units x PKR {price} = PKR {total:.2f}")

    cur.close()
    conn.close()
    return "\n".join(boq_lines)
