# backend/utils/price_processor.py
import pymysql
import numpy as np
import yaml
from datetime import date

with open("config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

OUTLIER_SIGMA = 1.5

def get_conn_local():
    return pymysql.connect(
        host=cfg["mysql"]["host"],
        user=cfg["mysql"]["user"],
        password=cfg["mysql"]["password"],
        db=cfg["mysql"]["db"],
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4"
    )

def aggregate_yearly_prices(year):
    conn = get_conn_local()
    cur = conn.cursor()

    cur.execute(
        "SELECT material_name, canonical_material_id, price_pkr, unit "
        "FROM material_price_raw WHERE year=%s",
        (year,)
    )
    raws = cur.fetchall()

    groups = {}
    for r in raws:
        if r["canonical_material_id"] is not None:
            key = int(r["canonical_material_id"])
        else:
            key = r["material_name"].strip().lower()

        groups.setdefault(key, []).append(r)

    for key, items in groups.items():
        prices = [float(i["price_pkr"]) for i in items if i["price_pkr"] is not None]
        if not prices:
            continue

        a = np.array(prices)
        mean = float(a.mean())
        std = float(a.std(ddof=0))

        if std > 0:
            mask = np.abs(a - mean) <= OUTLIER_SIGMA * std
            filtered = a[mask]
            if len(filtered) == 0:
                filtered = a
        else:
            filtered = a

        final_mean = float(filtered.mean())

        # resolve material_id
        if isinstance(key, int):
            material_id = key
        else:
            cur.execute(
                "SELECT material_id FROM materials WHERE LOWER(material_name)=LOWER(%s)",
                (key,)
            )
            row = cur.fetchone()
            material_id = row["material_id"] if row else None

        if not material_id:
            continue

        unit_val = items[0].get("unit", "")

        cur.execute(
            "INSERT INTO material_price_history "
            "(material_id, year, price_pkr, unit, effective_date) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE price_pkr=VALUES(price_pkr), "
            "unit=VALUES(unit), effective_date=VALUES(effective_date)",
            (material_id, year, final_mean, unit_val, date(year, 1, 1))
        )

    conn.commit()
    cur.close()
    conn.close()

def compute_inflation_for_material(material_id, year):
    conn = get_conn_local()
    cur = conn.cursor()

    cur.execute(
        "SELECT price_pkr FROM material_price_history WHERE material_id=%s AND year=%s",
        (material_id, year)
    )
    cur_r = cur.fetchone()

    cur.execute(
        "SELECT price_pkr FROM material_price_history WHERE material_id=%s AND year=%s",
        (material_id, year - 1)
    )
    prev_r = cur.fetchone()

    if not cur_r or not prev_r:
        cur.close()
        conn.close()
        return None

    inflation = (float(cur_r["price_pkr"]) - float(prev_r["price_pkr"])) / float(prev_r["price_pkr"])

    cur.execute(
        "INSERT INTO material_inflation_index (material_id, year, inflation_rate) "
        "VALUES (%s,%s,%s) "
        "ON DUPLICATE KEY UPDATE inflation_rate=VALUES(inflation_rate)",
        (material_id, year, inflation)
    )

    conn.commit()
    cur.close()
    conn.close()
    return inflation

def recompute_all(years):
    for y in years:
        aggregate_yearly_prices(y)

    conn = get_conn_local()
    cur = conn.cursor()
    cur.execute("SELECT material_id FROM materials")
    mats = cur.fetchall()
    cur.close()
    conn.close()

    for m in mats:
        for y in years:
            compute_inflation_for_material(m["material_id"], y)
