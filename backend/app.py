from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import subprocess
import json
import os
import hashlib
import pymysql
import yaml

# Load config
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

app = FastAPI(title="Road Cost Prediction API - Redesigned")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATA MODELS
# ============================================================================

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    username: str
    password: str

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class ProjectInput(BaseModel):
    project_name: str
    location: str
    location_type: str
    max_budget_pkr: float
    parent_company: str
    road_length_km: float
    road_width_m: float
    project_type: str
    soil_type: str = "normal"
    traffic_volume: str = "medium"

class MaterialPriceUpdate(BaseModel):
    material_id: int
    price_current: float

class TenderTrainingData(BaseModel):
    tender_no: str
    project_name: str
    organization: str
    location: str
    location_type: str
    parent_company: str
    road_length_km: float
    road_width_m: float
    project_type: str
    traffic_volume: str
    soil_type: str
    actual_cost_pkr: float
    boq_items: List[dict] # [{material_name, quantity, unit, unit_price}]

# ============================================================================
# AUTHENTICATION
# ============================================================================

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login for admin and employees"""
    conn = get_conn()
    cur = conn.cursor()

    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    cur.execute("""
        SELECT user_id, name, email, role FROM users
        WHERE username=%s AND password_hash=%s
    """, (credentials.username, password_hash))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "user_id": user['user_id'],
        "name": user['name'],
        "email": user['email'],
        "role": user['role'],
        "token": f"user_{user['user_id']}"
    }

@app.post("/api/auth/change-password")
async def change_password(user_id: int, password_data: PasswordChange):
    """Change user password"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify old password
    old_hash = hashlib.sha256(password_data.old_password.encode()).hexdigest()
    cur.execute("SELECT 1 FROM users WHERE user_id=%s AND password_hash=%s", (user_id, old_hash))

    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Incorrect old password")

    # Update password
    new_hash = hashlib.sha256(password_data.new_password.encode()).hexdigest()
    cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (new_hash, user_id))
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Password changed successfully"}

# ============================================================================
# ADMIN: USER MANAGEMENT
# ============================================================================

@app.post("/api/admin/create-user")
async def admin_create_user(admin_id: int, user_data: UserCreate):
    """Admin creates employee account"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Only admins can create users")

    # Check if username exists
    cur.execute("SELECT 1 FROM users WHERE username=%s", (user_data.username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create user
    password_hash = hashlib.sha256(user_data.password.encode()).hexdigest()
    cur.execute("""
        INSERT INTO users (name, email, phone, username, password_hash, role, created_by)
        VALUES (%s, %s, %s, %s, %s, 'employee', %s)
    """, (user_data.name, user_data.email, user_data.phone, user_data.username, password_hash, admin_id))

    conn.commit()
    user_id = cur.lastrowid
    cur.close()
    conn.close()

    return {"message": "User created successfully", "user_id": user_id}

@app.get("/api/admin/users")
async def get_all_users(admin_id: int):
    """Get all employees (admin only)"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all users except admin
    cur.execute("""
        SELECT user_id, name, email, phone, username, role, created_at
        FROM users
        WHERE role='employee'
        ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()

    return [{"user_id": u['user_id'], "name": u['name'], "email": u['email'],
            "phone": u['phone'], "username": u['username'],
            "created_at": u['created_at'].strftime("%Y-%m-%d %H:%M")} for u in users]

@app.delete("/api/admin/delete-user/{user_id}")
async def delete_user(admin_id: int, user_id: int):
    """Admin deletes employee (projects remain)"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if user is employee
    cur.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
    target = cur.fetchone()

    if not target:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    if target['role'] == 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete admin account")

    # Delete user (CASCADE will delete their projects)
    cur.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "User deleted successfully"}

# ============================================================================
# ADMIN: MATERIAL PRICE MANAGEMENT
# ============================================================================

@app.get("/api/admin/materials-prices")
async def get_all_materials_prices(admin_id: int):
    """Get all materials with prices (admin only)"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get materials with prices
    cur.execute("""
        SELECT m.material_id, m.material_name, m.unit, mc.category_name,
               mp.price_2023, mp.price_2024, mp.price_current,
               mp.last_updated_at
        FROM materials m
        LEFT JOIN material_categories mc ON m.category_id = mc.category_id
        LEFT JOIN material_prices mp ON m.material_id = mp.material_id
        ORDER BY mc.display_order, m.material_name
    """)
    materials = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "material_id": m['material_id'],
        "material_name": m['material_name'],
        "unit": m['unit'],
        "category": m['category_name'],
        "price_2023": float(m['price_2023'] or 0),
        "price_2024": float(m['price_2024'] or 0),
        "price_current": float(m['price_current'] or 0),
        "last_updated": m['last_updated_at'].strftime("%Y-%m-%d %H:%M") if m['last_updated_at'] else None
    } for m in materials]

@app.post("/api/admin/update-material-prices")
async def update_material_prices(admin_id: int, updates: List[MaterialPriceUpdate]):
    """Admin updates material prices (bulk update)"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Update prices
    for update in updates:
        cur.execute("""
            UPDATE material_prices
            SET price_current=%s, last_updated_by=%s
            WHERE material_id=%s
        """, (update.price_current, admin_id, update.material_id))

    conn.commit()
    cur.close()
    conn.close()

    return {"message": f"Updated {len(updates)} material prices successfully"}

# ============================================================================
# PROJECT PREDICTION
# ============================================================================

def get_material_prices_dict():
    """Get current material prices from database"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.material_name, mp.price_current
        FROM materials m
        JOIN material_prices mp ON m.material_id = mp.material_id
    """)
    prices = {row['material_name']: float(row['price_current']) for row in cur.fetchall()}
    cur.close()
    conn.close()
    return prices

def get_material_climate_impacts_dict():
    """Get climate impact factors from database"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.material_name, mci.emission_factor_kg_co2_per_kg,
               mci.energy_consumption_mj, mci.water_usage_liters
        FROM materials m
        JOIN material_climatic_impact mci ON m.material_id = mci.material_id
    """)
    impacts = {}
    for row in cur.fetchall():
        impacts[row['material_name']] = {
            'co2': float(row['emission_factor_kg_co2_per_kg']),
            'energy': float(row['energy_consumption_mj'] or 0),
            'water': float(row['water_usage_liters'] or 0)
        }
    cur.close()
    conn.close()
    return impacts

def estimate_material_quantities(project_data):
    """
    Estimate material quantities based on project specs
    Returns quantities in their billing units (MT, bags, kg, cft, etc.)
    """
    area_sqm = project_data.road_length_km * 1000 * project_data.road_width_m
    length_km = project_data.road_length_km
    
    # Road type multipliers
    multipliers = {
        "rural_road": {"cement": 0.35, "bitumen": 0.40, "steel": 0.25, "aggregate": 0.50, "sand": 0.50},
        "urban_road": {"cement": 0.70, "bitumen": 0.75, "steel": 0.60, "aggregate": 0.80, "sand": 0.80},
        "highway": {"cement": 1.0, "bitumen": 1.0, "steel": 1.0, "aggregate": 1.0, "sand": 1.0},
        "expressway": {"cement": 1.40, "bitumen": 1.35, "steel": 1.50, "aggregate": 1.30, "sand": 1.20}
    }
    mult = multipliers.get(project_data.project_type.lower().strip(), multipliers["highway"])
    
    materials = {}
    
    # INCREASED BASE QUANTITIES for more realistic expressway costs
    # Bitumen (Metric Tons) - Increased from 8kg/m² to 12kg/m² for thicker asphalt
    materials["Bitumen 60/70"] = area_sqm * 0.012 * mult["bitumen"]  # Was 0.008
    materials["Bitumen 80/100"] = area_sqm * 0.003 * mult["bitumen"]  # Was 0.002
    
    # Asphalt mixes (Metric Tons) - Increased for thicker wearing course
    materials["Asphaltic Concrete (Mix)"] = area_sqm * 0.150 * mult["bitumen"]  # Was 0.100
    materials["Premix Carpet (Mix)"] = area_sqm * 0.075 * mult["bitumen"]  # Was 0.050
    
    # Cement (50 kg bags) - Increased from 35kg/m² to 50kg/m² for stronger base
    cement_kg_per_sqm = 50 * mult["cement"]  # Was 35
    materials["Cement OPC Grade 53"] = (area_sqm * cement_kg_per_sqm) / 50
    materials["Cement PPC"] = (area_sqm * cement_kg_per_sqm * 0.3) / 50
    
    # Steel (kg) - Increased for heavy-duty reinforcement
    materials["Steel Bar 10mm"] = area_sqm * 4.5 * mult["steel"]  # Was 3
    materials["Steel Bar 16mm"] = area_sqm * 3.0 * mult["steel"]  # Was 2
    materials["Steel Mesh"] = area_sqm * 0.4 * mult["steel"]  # Was 0.3
    
    # Aggregates (cft) - Increased layer thickness
    base_thickness_m = 0.20  # Was 0.15 (200mm instead of 150mm)
    subbase_thickness_m = 0.30  # Was 0.25 (300mm instead of 250mm)
    
    base_volume_m3 = area_sqm * base_thickness_m
    subbase_volume_m3 = area_sqm * subbase_thickness_m
    
    materials["Crushed Stone 20mm"] = base_volume_m3 * 35.315 * 0.5 * mult["aggregate"]
    materials["Crushed Stone 40mm"] = subbase_volume_m3 * 35.315 * 0.4 * mult["aggregate"]
    materials["Bajri (Sargodha/Deena)"] = subbase_volume_m3 * 35.315 * 0.3 * mult["aggregate"]
    materials["Brick Ballast (Rora)"] = subbase_volume_m3 * 35.315 * 0.2 * mult["aggregate"]
    materials["Kankar"] = subbase_volume_m3 * 35.315 * 0.1 * mult["aggregate"]
    
    # Sand (cft) - Increased leveling layer
    sand_volume_m3 = area_sqm * 0.075  # Was 0.05 (75mm instead of 50mm)
    materials["Ravi Sand"] = sand_volume_m3 * 35.315 * 0.6 * mult["sand"]
    materials["Chenab Sand"] = sand_volume_m3 * 35.315 * 0.4 * mult["sand"]
    
    # Additives (Metric Tons) - Increased for better soil stabilization
    materials["Hydrated Lime"] = area_sqm * 0.0015 * mult["cement"]  # Was 0.001
    materials["Fly Ash"] = area_sqm * 0.003 * mult["cement"]  # Was 0.002
    
    # Road furniture and accessories - Increased for expressway standards
    materials["Thermoplastic Paint"] = length_km * 200  # Was 150
    materials["Glass Beads"] = length_km * 20  # Was 15
    materials["RCC Pipe 300mm"] = length_km * 150  # Was 100
    materials["PVC Pipe 200mm"] = length_km * 75  # Was 50
    materials["W-Beam Guardrail"] = length_km * 300 * mult["steel"]  # Was 200
    materials["Road Sign (Aluminum)"] = length_km * 15  # Was 10
    
    # Terrain adjustment
    if project_data.location_type.lower().strip() == "mountainous":
        for key in ["Cement OPC Grade 53", "Steel Bar 10mm", "Steel Bar 16mm",
                   "Crushed Stone 20mm", "Bitumen 60/70", "W-Beam Guardrail"]:
            if key in materials:
                materials[key] *= 1.25
    
    # Traffic adjustment
    traffic_mult = {"low": 0.85, "medium": 1.0, "high": 1.20}.get(
        project_data.traffic_volume.lower().strip(), 1.0
    )
    for key in ["Bitumen 60/70", "Asphaltic Concrete (Mix)", "Cement OPC Grade 53",
               "Steel Bar 10mm", "Thermoplastic Paint"]:
        if key in materials:
            materials[key] *= traffic_mult
    
    return materials

@app.post("/api/predict")
async def predict_project(project_data: ProjectInput, user_id: int):
    """Predict project cost and generate report"""
    try:
        # Get prices and climate impacts from database
        prices = get_material_prices_dict()
        climate_impacts = get_material_climate_impacts_dict()

        # Estimate materials
        materials_qty = estimate_material_quantities(project_data)

        # Calculate costs and climate impact
        total_cost = 0
        total_co2_kg = 0
        total_energy = 0
        total_water = 0
        boq_list = []
        climate_list = []

        conn = get_conn()
        cur = conn.cursor()

        # Get material IDs and categories
        cur.execute("""
            SELECT m.material_id, m.material_name, m.unit, mc.category_name
            FROM materials m
            LEFT JOIN material_categories mc ON m.category_id = mc.category_id
        """)
        material_info = {row['material_name']: row for row in cur.fetchall()}

        for mat_name, qty_in_correct_unit in materials_qty.items():
            if qty_in_correct_unit < 0.01:
                continue

            mat_info = material_info.get(mat_name)
            if not mat_info:
                continue

            unit_price = prices.get(mat_name, 0)
            cost = qty_in_correct_unit * unit_price
            total_cost += cost

            # Climate impact calculation
            impact = climate_impacts.get(mat_name, {})
            
            # For climate, we need kg - convert if necessary
            if "Metric Ton" in mat_info['unit']:
                qty_kg = qty_in_correct_unit * 1000
            elif "50 kg Bag" in mat_info['unit']:
                qty_kg = qty_in_correct_unit * 50
            elif mat_info['unit'] in ['Cubic Foot (cft)', 'Running Meter (RM)', 'Square Foot (ft²)', 'Square Meter (m²)']:
                # For volume/area units, estimate weight (varies by material)
                # Rough estimates: 1 cft stone = 45kg, 1 RM pipe = 50kg, 1 m² mesh = 5kg
                if 'Stone' in mat_name or 'Bajri' in mat_name or 'Ballast' in mat_name:
                    qty_kg = qty_in_correct_unit * 45  # 45 kg per cft
                elif 'Sand' in mat_name:
                    qty_kg = qty_in_correct_unit * 40  # 40 kg per cft
                elif 'Pipe' in mat_name:
                    qty_kg = qty_in_correct_unit * 50  # 50 kg per RM
                elif 'Mesh' in mat_name:
                    qty_kg = qty_in_correct_unit * 5  # 5 kg per m²
                else:
                    qty_kg = qty_in_correct_unit  # Default: assume kg
            else:
                qty_kg = qty_in_correct_unit  # Already in kg
            
            co2_kg = qty_kg * impact.get('co2', 0)
            energy_mj = qty_kg * impact.get('energy', 0)
            water_l = qty_kg * impact.get('water', 0)

            total_co2_kg += co2_kg
            total_energy += energy_mj
            total_water += water_l

            # Store BOQ
            boq_list.append({
                'material_id': mat_info['material_id'],
                'material_name': mat_name,
                'quantity': qty_in_correct_unit,
                'unit': mat_info['unit'],
                'unit_price': unit_price,
                'total_cost': cost,
                'category': mat_info['category_name']
            })

            # Store climate impact
            climate_list.append({
                'material_id': mat_info['material_id'],
                'quantity_kg': qty_kg,
                'co2_kg': co2_kg,
                'energy_mj': energy_mj,
                'water_l': water_l
            })
                
        db_boq = cur.fetchall()
        print("First 10 items retrieved from database:")
        for row in db_boq:
            print(f"  {row['material_name']:40s}: {row['quantity']:>12,.2f} {row['unit']:20s} "
                  f"× PKR {row['unit_price_pkr']:>10,.0f} = PKR {row['total_cost_pkr']:>15,.0f}")
        
        print("="*100 + "\n")

        # Calculate budget status
        within_budget = total_cost <= project_data.max_budget_pkr
        budget_status = "Within Budget" if within_budget else "Over Budget"
        budget_diff = project_data.max_budget_pkr - total_cost
        budget_util = (total_cost / project_data.max_budget_pkr) * 100

        # Insert project
        area_hectares = (project_data.road_length_km * 1000 * project_data.road_width_m) / 10000
        cur.execute("""
            INSERT INTO projects
            (user_id, project_name, location, location_type, parent_company,
             road_length_km, road_width_m, area_hectares, project_type,
             traffic_volume, soil_type, max_budget_pkr)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, project_data.project_name, project_data.location,
              project_data.location_type, project_data.parent_company,
              project_data.road_length_km, project_data.road_width_m, area_hectares,
              project_data.project_type, project_data.traffic_volume,
              project_data.soil_type, project_data.max_budget_pkr))

        project_id = cur.lastrowid

        # Insert prediction
        cur.execute("""
            INSERT INTO project_predictions
            (project_id, predicted_cost_pkr, total_co2_emissions_tons,
             total_energy_mj, total_water_liters, budget_status,
             budget_difference_pkr, budget_utilization_percent, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'v2.0')
        """, (project_id, total_cost, total_co2_kg/1000, total_energy, total_water,
              budget_status, budget_diff, budget_util))

        # Insert BOQ items
        for item in boq_list:
            cur.execute("""
                INSERT INTO project_boq
                (project_id, material_id, quantity, unit, unit_price_pkr, total_cost_pkr, category_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (project_id, item['material_id'], item['quantity'], item['unit'],
                  item['unit_price'], item['total_cost'], item['category']))

        # Insert climate impact
        for item in climate_list:
            cur.execute("""
                INSERT INTO project_climate_impact
                (project_id, material_id, quantity_kg, co2_emissions_kg,
                 energy_consumption_mj, water_usage_liters)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (project_id, item['material_id'], item['quantity_kg'],
                  item['co2_kg'], item['energy_mj'], item['water_l']))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "project_id": project_id,
            "project_name": project_data.project_name,
            "predicted_cost": total_cost,
            "co2_emissions_tons": total_co2_kg / 1000,
            "budget_status": budget_status,
            "within_budget": within_budget,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
def generate_project_report_text(project, boq, climate, recommendations):
    """Generate formatted text report for PDF"""
    
    report = []
    report.append("="*80)
    report.append("ROAD CONSTRUCTION PROJECT - COST ESTIMATION REPORT")
    report.append("="*80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Project Details
    report.append("PROJECT DETAILS:")
    report.append("-"*80)
    report.append(f"Project Name:        {project['project_name']}")
    report.append(f"Location:            {project['location']}")
    report.append(f"Location Type:       {project['location_type'].title()}")
    report.append(f"Company:             {project['parent_company']}")
    report.append(f"Project Type:        {project['project_type'].replace('_', ' ').title()}")
    report.append(f"Traffic Volume:      {project['traffic_volume'].title()}")
    report.append(f"Soil Type:           {project['soil_type'].title()}")
    report.append("")
    
    # Road Specifications
    report.append("ROAD SPECIFICATIONS:")
    report.append("-"*80)
    report.append(f"Road Length:         {project['road_length_km']:.2f} km")
    report.append(f"Road Width:          {project['road_width_m']:.2f} m")
    report.append(f"Total Area:          {project['area_hectares']:.2f} hectares")
    report.append("")
    
    # Cost Prediction
    report.append("COST PREDICTION:")
    report.append("-"*80)
    report.append(f"**TOTAL PREDICTED COST:  PKR {project['predicted_cost_pkr']:,.2f}**")
    report.append(f"Maximum Budget:          PKR {project['max_budget_pkr']:,.2f}")
    report.append(f"Budget Status:           {project['budget_status']}")
    report.append(f"Budget Difference:       PKR {project['budget_difference']:,.2f}")
    report.append(f"Budget Utilization:      {project['budget_utilization']:.1f}%")
    report.append(f"Cost per Kilometer:      PKR {project['predicted_cost_pkr']/project['road_length_km']:,.2f}")
    report.append("")
    
    # Environmental Impact
    report.append("ENVIRONMENTAL IMPACT:")
    report.append("-"*80)
    report.append(f"Total CO2 Emissions:     {project['co2_emissions_tons']:,.2f} tons")
    report.append(f"CO2 per km:              {project['co2_emissions_tons']/project['road_length_km']:,.2f} tons/km")
    report.append("")
    
    # Bill of Quantities
    report.append("DETAILED BILL OF QUANTITIES (BOQ):")
    report.append("="*80)
    
    # Group by category
    categories = {}
    for item in boq:
        cat = item['category'] or 'Other'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    for category, items in sorted(categories.items()):
        report.append(f"\n{category}:")
        report.append("-"*80)
        category_total = 0
        for item in items:
            report.append(f"{item['material_name']:40s} {item['quantity']:>12,.2f} {item['unit']:15s}")
            report.append(f"  Unit Price: PKR {item['unit_price']:>12,.2f}  |  Total: PKR {item['total_cost']:>15,.2f}")
            category_total += item['total_cost']
        report.append(f"{'Category Subtotal:':56s} PKR {category_total:>15,.2f}")
        report.append("")
    
    report.append("="*80)
    report.append(f"**TOTAL MATERIALS COST (BOQ):            PKR {project['predicted_cost_pkr']:>15,.2f}**")
    report.append("="*80)
    report.append("")
    
    # Recommendations
    if recommendations:
        report.append("SUSTAINABILITY RECOMMENDATIONS:")
        report.append("="*80)
        for rec in recommendations:
            report.append(f"\n{rec['group']}:")
            report.append(f"  {rec['text']}")
            if rec['reduction_percent'] > 0:
                report.append(f"  Potential Reduction: {rec['reduction_percent']:.1f}%")
        report.append("")
    
    # Footer
    report.append("="*80)
    report.append("NOTES:")
    report.append("- All costs are in Pakistani Rupees (PKR)")
    report.append("- Prices based on 2025 market rates")
    report.append("- Material quantities calculated using standard construction practices")
    report.append("- Additional costs (labor, equipment, overhead) not included")
    report.append("="*80)
    report.append("")
    report.append("Report generated by Road Cost Prediction System")
    report.append(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*80)
    
    return "\n".join(report)


@app.get("/api/project/{project_id}/download-report")
async def download_project_report(project_id: int):
    """Generate and download PDF report for a project"""
    try:
        # Import PDF library
        from backend.utils.pdf_output import generate_output_pdf
        
        # Get project details
        conn = get_conn()
        cur = conn.cursor()
        
        # Get project info
        cur.execute("""
            SELECT p.*, pp.predicted_cost_pkr, pp.total_co2_emissions_tons,
                   pp.budget_status, pp.budget_difference_pkr, pp.budget_utilization_percent
            FROM projects p
            LEFT JOIN project_predictions pp ON p.project_id = pp.project_id
            WHERE p.project_id = %s
        """, (project_id,))
        project = cur.fetchone()
        
        if not project:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get BOQ
        cur.execute("""
            SELECT pb.*, m.material_name
            FROM project_boq pb
            JOIN materials m ON pb.material_id = m.material_id
            WHERE pb.project_id = %s
            ORDER BY pb.category_name, m.material_name
        """, (project_id,))
        boq = cur.fetchall()
        
        # Get recommendations
        cur.execute("SELECT * FROM climate_recommendations ORDER BY priority DESC")
        recommendations = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to dict format for report generation
        project_dict = {
            'project_id': project['project_id'],
            'project_name': project['project_name'],
            'location': project['location'],
            'location_type': project['location_type'],
            'parent_company': project['parent_company'],
            'road_length_km': float(project['road_length_km']),
            'road_width_m': float(project['road_width_m']),
            'area_hectares': float(project['area_hectares'] or 0),
            'project_type': project['project_type'],
            'traffic_volume': project['traffic_volume'],
            'soil_type': project['soil_type'],
            'max_budget_pkr': float(project['max_budget_pkr']),
            'predicted_cost_pkr': float(project['predicted_cost_pkr'] or 0),
            'co2_emissions_tons': float(project['total_co2_emissions_tons'] or 0),
            'budget_status': project['budget_status'],
            'budget_difference': float(project['budget_difference_pkr'] or 0),
            'budget_utilization': float(project['budget_utilization_percent'] or 0)
        }
        
        boq_list = [{
            'material_name': b['material_name'],
            'quantity': float(b['quantity']),
            'unit': b['unit'],
            'unit_price': float(b['unit_price_pkr']),
            'total_cost': float(b['total_cost_pkr']),
            'category': b['category_name']
        } for b in boq]
        
        rec_list = [{
            'group': r['group_name'],
            'text': r['recommendation_text'],
            'reduction_percent': float(r['potential_reduction_percent'] or 0)
        } for r in recommendations]
        
        # Generate report text
        report_text = generate_project_report_text(project_dict, boq_list, [], rec_list)
        
        # Create downloads directory if it doesn't exist
        os.makedirs("downloads", exist_ok=True)
        
        # Generate PDF filename
        pdf_filename = f"project_{project_id}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join("downloads", pdf_filename)
        
        # Generate PDF
        generate_output_pdf(pdf_path, project_dict, report_text)
        
        # Return file
        return FileResponse(
            path=pdf_path,
            filename=pdf_filename,
            media_type='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename={pdf_filename}"
            }
        )
        
    except Exception as e:
        print(f"[ERROR] PDF generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")
     

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

@app.get("/api/projects/{user_id}")
async def get_user_projects(user_id: int, location_type: Optional[str] = None,
                          min_budget: Optional[float] = None, max_budget: Optional[float] = None):
    """Get user's projects with filters"""
    conn = get_conn()
    cur = conn.cursor()

    query = """
        SELECT p.project_id, p.project_name, p.location, p.location_type,
               p.max_budget_pkr, p.created_at,
               pp.predicted_cost_pkr, pp.total_co2_emissions_tons, pp.budget_status
        FROM projects p
        LEFT JOIN project_predictions pp ON p.project_id = pp.project_id
        WHERE p.user_id = %s
    """
    params = [user_id]

    if location_type:
        query += " AND p.location_type = %s"
        params.append(location_type)

    if min_budget is not None:
        query += " AND p.max_budget_pkr >= %s"
        params.append(min_budget)

    if max_budget is not None:
        query += " AND p.max_budget_pkr <= %s"
        params.append(max_budget)

    query += " ORDER BY p.created_at DESC"

    cur.execute(query, tuple(params))
    projects = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "project_id": p['project_id'],
        "project_name": p['project_name'],
        "location": p['location'],
        "location_type": p['location_type'],
        "max_budget": float(p['max_budget_pkr']),
        "predicted_cost": float(p['predicted_cost_pkr'] or 0),
        "co2_emissions": float(p['total_co2_emissions_tons'] or 0),
        "budget_status": p['budget_status'],
        "created_at": p['created_at'].strftime("%Y-%m-%d %H:%M")
    } for p in projects]

@app.get("/api/admin/all-projects")
async def get_all_projects(admin_id: int, location_type: Optional[str] = None,
                          min_budget: Optional[float] = None, max_budget: Optional[float] = None):
    """Admin gets all projects with filters"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    query = """
        SELECT p.project_id, p.project_name, p.location, p.location_type,
               p.max_budget_pkr, p.created_at, u.name as user_name,
               pp.predicted_cost_pkr, pp.total_co2_emissions_tons, pp.budget_status
        FROM projects p
        LEFT JOIN users u ON p.user_id = u.user_id
        LEFT JOIN project_predictions pp ON p.project_id = pp.project_id
        WHERE 1=1
    """
    params = []

    if location_type:
        query += " AND p.location_type = %s"
        params.append(location_type)

    if min_budget is not None:
        query += " AND p.max_budget_pkr >= %s"
        params.append(min_budget)

    if max_budget is not None:
        query += " AND p.max_budget_pkr <= %s"
        params.append(max_budget)

    query += " ORDER BY p.created_at DESC"

    cur.execute(query, tuple(params))
    projects = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "project_id": p['project_id'],
        "project_name": p['project_name'],
        "user_name": p['user_name'],
        "location": p['location'],
        "location_type": p['location_type'],
        "max_budget": float(p['max_budget_pkr']),
        "predicted_cost": float(p['predicted_cost_pkr'] or 0),
        "co2_emissions": float(p['total_co2_emissions_tons'] or 0),
        "budget_status": p['budget_status'],
        "created_at": p['created_at'].strftime("%Y-%m-%d %H:%M")
    } for p in projects]

@app.get("/api/project/{project_id}/details")
async def get_project_details(project_id: int):
    """Get complete project details"""
    conn = get_conn()
    cur = conn.cursor()

    # Get project info
    cur.execute("""
        SELECT p.*, pp.predicted_cost_pkr, pp.total_co2_emissions_tons,
               pp.total_energy_mj, pp.total_water_liters, pp.budget_status,
               pp.budget_difference_pkr, pp.budget_utilization_percent
        FROM projects p
        LEFT JOIN project_predictions pp ON p.project_id = pp.project_id
        WHERE p.project_id = %s
    """, (project_id,))
    project = cur.fetchone()

    if not project:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    # Get BOQ
    cur.execute("""
        SELECT pb.*, m.material_name
        FROM project_boq pb
        JOIN materials m ON pb.material_id = m.material_id
        WHERE pb.project_id = %s
        ORDER BY pb.category_name, m.material_name
    """, (project_id,))
    boq = cur.fetchall()

    # Get climate impact
    cur.execute("""
        SELECT pci.*, m.material_name
        FROM project_climate_impact pci
        JOIN materials m ON pci.material_id = m.material_id
        WHERE pci.project_id = %s
    """, (project_id,))
    climate = cur.fetchall()

    # Get recommendations
    cur.execute("SELECT * FROM climate_recommendations ORDER BY priority DESC, group_name")
    recommendations = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "project": {
            "project_id": project['project_id'],
            "project_name": project['project_name'],
            "location": project['location'],
            "location_type": project['location_type'],
            "parent_company": project['parent_company'],
            "road_length_km": float(project['road_length_km']),
            "road_width_m": float(project['road_width_m']),
            "area_hectares": float(project['area_hectares'] or 0),
            "project_type": project['project_type'],
            "traffic_volume": project['traffic_volume'],
            "soil_type": project['soil_type'],
            "max_budget_pkr": float(project['max_budget_pkr']),
            "predicted_cost_pkr": float(project['predicted_cost_pkr'] or 0),
            "co2_emissions_tons": float(project['total_co2_emissions_tons'] or 0),
            "budget_status": project['budget_status'],
            "budget_difference": float(project['budget_difference_pkr'] or 0),
            "budget_utilization": float(project['budget_utilization_percent'] or 0)
        },
        "boq": [{
            "material_name": b['material_name'],
            "quantity": float(b['quantity']),
            "unit": b['unit'],
            "unit_price": float(b['unit_price_pkr']),
            "total_cost": float(b['total_cost_pkr']),
            "category": b['category_name']
        } for b in boq],
        "climate_impact": [{
            "material_name": c['material_name'],
            "quantity_kg": float(c['quantity_kg']),
            "co2_kg": float(c['co2_emissions_kg']),
            "energy_mj": float(c['energy_consumption_mj']),
            "water_l": float(c['water_usage_liters'])
        } for c in climate],
        "recommendations": [{
            "group": r['group_name'],
            "text": r['recommendation_text'],
            "reduction_percent": float(r['potential_reduction_percent'] or 0),
            "priority": r['priority']
        } for r in recommendations]
    }

@app.delete("/api/project/{project_id}")
async def delete_project(project_id: int, user_id: int):
    """Delete project (CASCADE deletes all related data)"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify project ownership
    cur.execute("SELECT user_id FROM projects WHERE project_id=%s", (project_id,))
    project = cur.fetchone()

    if not project:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    if project['user_id'] != user_id:
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    # Delete project (CASCADE will delete predictions, BOQ, climate impact)
    cur.execute("DELETE FROM projects WHERE project_id=%s", (project_id,))
    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Project deleted successfully"}

# ============================================================================
# ADMIN: ADD TRAINING DATA
# ============================================================================

@app.post("/api/admin/add-training-data")
async def add_training_data(admin_id: int, tender_data: TenderTrainingData):
    """Admin adds historical project data for ML training"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Insert tender
        cur.execute("""
            INSERT INTO tenders 
            (tender_no, organization, project_name, location, location_type,
             parent_company, road_length_km, road_width_m, project_type,
             traffic_volume, soil_type, actual_cost_pkr, boq_json, used_for_training)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (tender_data.tender_no, tender_data.organization, tender_data.project_name,
              tender_data.location, tender_data.location_type, tender_data.parent_company,
              tender_data.road_length_km, tender_data.road_width_m, tender_data.project_type,
              tender_data.traffic_volume, tender_data.soil_type, tender_data.actual_cost_pkr,
              json.dumps(tender_data.boq_items)))
        
        tender_id = cur.lastrowid
        
        # Prepare ML features (same as prediction logic)
        area_sqm = tender_data.road_length_km * 1000 * tender_data.road_width_m
        
        # Calculate material totals from BOQ
        cement_qty = sum([item['quantity'] for item in tender_data.boq_items 
                         if 'cement' in item['material_name'].lower()]) / 1000  # tons
        bitumen_qty = sum([item['quantity'] for item in tender_data.boq_items 
                          if 'bitumen' in item['material_name'].lower()]) / 1000
        steel_qty = sum([item['quantity'] for item in tender_data.boq_items 
                        if 'steel' in item['material_name'].lower()]) / 1000
        
        # Get average prices
        prices = get_material_prices_dict()
        cement_price = prices.get('Cement OPC Grade 53', 1550)
        bitumen_price = prices.get('Bitumen 60/70', 175000)
        steel_price = prices.get('Steel Bar 10mm', 255)
        
        features = {
            "road_length_km": tender_data.road_length_km,
            "road_width_km": tender_data.road_width_m / 1000,
            "cement_qty_ton": cement_qty,
            "bitumen_qty_ton": bitumen_qty,
            "steel_qty_ton": steel_qty,
            "cement_price": cement_price,
            "bitumen_price": bitumen_price,
            "steel_price": steel_price,
            "materials_total": (cement_qty * cement_price * 20) + (bitumen_qty * bitumen_price) + (steel_qty * steel_price * 1000),
            "project_type": tender_data.project_type,
            "location_type": tender_data.location_type,
            "traffic_volume": tender_data.traffic_volume
        }
        
        # Insert ML training data
        cur.execute("""
            INSERT INTO ml_training_data 
            (tender_id, features_json, label_cost_pkr, data_quality)
            VALUES (%s, %s, %s, 'High')
        """, (tender_id, json.dumps(features), tender_data.actual_cost_pkr))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "message": "Training data added successfully",
            "tender_id": tender_id,
            "can_retrain_model": True
        }
        
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"[ERROR] Failed to add training data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/training-data-count")
async def get_training_data_count(admin_id: int):
    """Get count of training data entries"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    cur.execute("SELECT COUNT(*) as count FROM ml_training_data")
    result = cur.fetchone()
    cur.close()
    conn.close()

    return {
        "training_data_count": result['count'],
        "min_required": 50,
        "can_retrain": result['count'] >= 50
    }

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "API is running"}

@app.post("/api/admin/retrain-model")
async def retrain_model(admin_id: int):
    """
    Admin triggers ML model retraining
    This runs the train_model.py script and updates the model
    """
    import sys  # Add this import at the top
    
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if enough training data exists
    cur.execute("SELECT COUNT(*) as count FROM ml_training_data WHERE label_cost_pkr > 0")
    result = cur.fetchone()
    training_count = result['count']

    if training_count < 50:
        cur.close()
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient training data. Need at least 50 records, have {training_count}"
        )

    # Log the retraining start
    cur.execute("""
        INSERT INTO model_training_logs (admin_id, status, training_data_count, started_at)
        VALUES (%s, 'in_progress', %s, NOW())
    """, (admin_id, training_count))
    log_id = cur.lastrowid
    conn.commit()

    try:
        # Run the training script
        print(f"[INFO] Starting model retraining with {training_count} records...")
        
        # FIXED: Use sys.executable to use the current Python interpreter (from venv)
        result = subprocess.run(
            [sys.executable, "backend/ml/train_model.py"],  # Changed from "python"
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=os.path.dirname(os.path.dirname(__file__))  # Set working directory to project root
        )

        if result.returncode == 0:
            # Training successful
            print("[SUCCESS] Model retrained successfully!")
            print(result.stdout)
            
            # Close existing connection and create fresh one for success update
            try:
                cur.close()
                conn.close()
            except:
                pass
            
            # Create fresh connection for success update
            conn = get_conn()
            cur = conn.cursor()
            
            # Update log (note: %% escapes % for Python string formatting)
            cur.execute("""
                UPDATE model_training_logs 
                SET status='completed', completed_at=NOW(), 
                    model_version=CONCAT('v', DATE_FORMAT(NOW(), '%%Y%%m%%d_%%H%%i%%s')),
                    log_output=%s
                WHERE log_id=%s
            """, (result.stdout, log_id))
            conn.commit()
            
            cur.close()
            conn.close()
            
            return {
                "message": "Model retrained successfully!",
                "training_data_count": training_count,
                "log_id": log_id,
                "status": "completed"
            }
        else:
            # Training failed
            print("[ERROR] Model retraining failed!")
            print(result.stderr)
            
            # Create a fresh connection for error handling
            conn = get_conn()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE model_training_logs 
                SET status='failed', completed_at=NOW(), error_message=%s
                WHERE log_id=%s
            """, (result.stderr, log_id))
            conn.commit()
            
            cur.close()
            conn.close()
            
            raise HTTPException(status_code=500, detail=f"Model training failed: {result.stderr}")

    except subprocess.TimeoutExpired:
        # Create a fresh connection for error handling
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE model_training_logs 
            SET status='failed', completed_at=NOW(), error_message='Training timeout (>10 minutes)'
            WHERE log_id=%s
        """, (log_id,))
        conn.commit()
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail="Model training timeout")

    except Exception as e:
        # Create a fresh connection for error handling
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE model_training_logs 
            SET status='failed', completed_at=NOW(), error_message=%s
            WHERE log_id=%s
        """, (str(e), log_id))
        conn.commit()
        cur.close()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/training-status")
async def get_training_status(admin_id: int):
    """Get current training status and history"""
    conn = get_conn()
    cur = conn.cursor()

    # Verify admin
    cur.execute("SELECT role FROM users WHERE user_id=%s", (admin_id,))
    admin = cur.fetchone()

    if not admin or admin['role'] != 'admin':
        cur.close()
        conn.close()
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get training data count
    cur.execute("SELECT COUNT(*) as count FROM ml_training_data WHERE label_cost_pkr > 0")
    data_count = cur.fetchone()['count']

    # Get latest training log
    cur.execute("""
        SELECT * FROM model_training_logs 
        ORDER BY started_at DESC 
        LIMIT 1
    """)
    latest_log = cur.fetchone()

    # Get training history
    cur.execute("""
        SELECT log_id, admin_id, status, training_data_count, model_version,
               started_at, completed_at
        FROM model_training_logs 
        ORDER BY started_at DESC 
        LIMIT 10
    """)
    history = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "training_data_count": data_count,
        "min_required": 50,
        "can_retrain": data_count >= 50,
        "latest_training": {
            "status": latest_log['status'] if latest_log else None,
            "training_data_count": latest_log['training_data_count'] if latest_log else 0,
            "model_version": latest_log['model_version'] if latest_log else None,
            "started_at": latest_log['started_at'].strftime("%Y-%m-%d %H:%M:%S") if latest_log and latest_log['started_at'] else None,
            "completed_at": latest_log['completed_at'].strftime("%Y-%m-%d %H:%M:%S") if latest_log and latest_log['completed_at'] else None
        } if latest_log else None,
        "training_history": [{
            "log_id": log['log_id'],
            "status": log['status'],
            "training_data_count": log['training_data_count'],
            "model_version": log['model_version'],
            "started_at": log['started_at'].strftime("%Y-%m-%d %H:%M:%S") if log['started_at'] else None,
            "completed_at": log['completed_at'].strftime("%Y-%m-%d %H:%M:%S") if log['completed_at'] else None
        } for log in history]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
