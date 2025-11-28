import pymysql
from datetime import date

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        db="road_costs",
        cursorclass=pymysql.cursors.DictCursor,
    )

def seed_material_price_history():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT material_id, material_name FROM materials")
    material_rows = cur.fetchall()
    materials_map = {row["material_name"].lower(): row["material_id"] for row in material_rows}

    rows = [
        ("Bitumen 60/70", "Metric Ton (MT)", 130000, 155000, 175000),
        ("Bitumen 80/100", "Metric Ton (MT)", 135000, 160000, 180000),
        ("Cement OPC Grade 53", "50 kg Bag", 900, 1150, 1550),
        ("Cement PPC", "50 kg Bag", 880, 1130, 1530),
        ("Steel Bar 10mm", "Kilogram (kg)", 220, 245, 255),
        ("Steel Bar 16mm", "Kilogram (kg)", 220, 245, 255),
        ("Crushed Stone 20mm", "Cubic Foot (cft)", 90, 135, 160),
        ("Crushed Stone 40mm", "Cubic Foot (cft)", 85, 125, 155),
        ("Bajri", "Cubic Foot (cft)", 95, 140, 165),
        ("Ravi Sand", "Cubic Foot (cft)", 30, 45, 55),
        ("Chenab Sand", "Cubic Foot (cft)", 55, 75, 85),
        ("Brick Ballast (Rora)", "Cubic Foot (cft)", 60, 80, 95),
        ("Kankar", "Cubic Foot (cft)", 25, 35, 45),
        ("Steel Mesh", "Square Meter (m²)", 500, 650, 750),
        ("Asphaltic Concrete (Mix)", "Metric Ton (MT)", 15000, 20000, 26000),
        ("Premix Carpet (Mix)", "Metric Ton (MT)", 14500, 19000, 25000),
        ("Thermoplastic Paint", "Kilogram (kg)", 280, 380, 500),
        ("Glass Beads", "Kilogram (kg)", 150, 200, 250),
        ("RCC Pipe 300mm", "Running Meter (RM)", 1200, 1600, 2200),
        ("PVC Pipe 200mm", "Running Meter (RM)", 900, 1300, 1800),
        ("W-Beam Guardrail", "Running Meter (RM)", 4500, 6000, 8000),
        ("Road Sign (Aluminum)", "Square Foot (ft²)", 1800, 2500, 3500),
        ("Hydrated Lime", "Metric Ton (MT)", 15000, 22000, 30000),
        ("Fly Ash", "Metric Ton (MT)", 8000, 11000, 15000),
    ]

    for mat, unit, y2023, y2024, y2025 in rows:
        mat_id = materials_map.get(mat.lower())
        if mat_id is None:
            continue

        for year, price in [(2023, y2023), (2024, y2024), (2025, y2025)]:
            cur.execute(
                """
                SELECT 1 FROM material_price_history
                WHERE material_id=%s AND year=%s
                """,
                (mat_id, year),
            )
            if cur.fetchone():
                continue

            cur.execute(
                """
                INSERT INTO material_price_history
                (material_id, year, avg_price, unit, effective_date)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (mat_id, year, price, unit, date(year, 1, 1)),
            )

    conn.commit()
    cur.close()
    conn.close()

def get_inflation_multiplier(year):
    multipliers = {2023: 1.00, 2024: 1.18, 2025: 1.32}
    return multipliers.get(year, 1.0)

def adjust_price_for_inflation(price, year):
    multiplier = get_inflation_multiplier(year)
    return price * multiplier
