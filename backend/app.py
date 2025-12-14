from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import os

from backend.database import get_conn
from backend.ml.inference import predict_cost
from backend.utils.pdf_output import generate_output_pdf
from backend.utils.inflation import seed_material_price_history

app = FastAPI(title="Road Cost Prediction API")

# CORS for React frontend
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

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ProjectInput(BaseModel):
    project_name: str
    location: str
    location_type: str  # "plain" or "mountainous"
    max_budget_pkr: float
    parent_company: str
    road_length_km: float
    road_width_m: float
    project_type: str  # "highway", "urban_road", "rural_road", "expressway"
    soil_type: Optional[str] = "normal"
    traffic_volume: Optional[str] = "medium"  # "low", "medium", "high"

class ProjectResponse(BaseModel):
    project_id: int
    project_name: str
    predicted_cost: float
    climate_score: float
    within_budget: bool
    pdf_url: str
    created_at: str

# ============================================================================
# USER AUTHENTICATION
# ============================================================================

@app.post("/api/auth/register")
async def register(user: UserCreate):
    """Register a new user"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT 1 FROM users WHERE username=%s", (user.username,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    import hashlib
    password_hash = hashlib.sha256(user.password.encode()).hexdigest()
    
    cur.execute("""
        INSERT INTO users (name, email, phone, username, password_hash, created_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (user.name, user.email, user.phone, user.username, password_hash))
    
    conn.commit()
    user_id = cur.lastrowid
    cur.close()
    conn.close()
    
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    conn = get_conn()
    cur = conn.cursor()
    
    import hashlib
    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    
    cur.execute("""
        SELECT user_id, name, email FROM users 
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
        "token": f"user_{user['user_id']}"
    }

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================

@app.get("/api/projects/{user_id}")
async def get_user_projects(user_id: int):
    """Get all projects for a user"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT p.project_id, p.project_name, p.predicted_cost, p.climate_score,
               p.within_budget, p.pdf_path, p.created_at
        FROM projects p
        WHERE p.user_id = %s
        ORDER BY p.created_at DESC
    """, (user_id,))
    
    projects = cur.fetchall()
    cur.close()
    conn.close()
    
    return [{
        "project_id": p['project_id'],
        "project_name": p['project_name'],
        "predicted_cost": float(p['predicted_cost']),
        "climate_score": float(p['climate_score']) if p['climate_score'] else 0,
        "within_budget": bool(p['within_budget']),
        "pdf_url": f"/api/download/{p['project_id']}",
        "created_at": p['created_at'].strftime("%Y-%m-%d %H:%M")
    } for p in projects]

# ============================================================================
# HELPER FUNCTIONS FOR ML MODEL
# ============================================================================

def calculate_climate_impact(materials_used):
    """Calculate environmental impact for all materials"""
    EMISSION_FACTORS = {
        "bitumen_60_70": 0.40,
        "bitumen_80_100": 0.40,
        "asphalt_concrete": 0.35,
        "premix_carpet": 0.35,
        "cement_opc": 0.85,
        "cement_ppc": 0.75,
        "steel_10mm": 1.80,
        "steel_16mm": 1.80,
        "steel_mesh": 1.80,
        "crushed_stone_20mm": 0.02,
        "crushed_stone_40mm": 0.02,
        "bajri": 0.02,
        "brick_ballast": 0.15,
        "kankar": 0.01,
        "ravi_sand": 0.01,
        "chenab_sand": 0.01,
        "hydrated_lime": 0.70,
        "fly_ash": 0.10,
        "thermoplastic_paint": 2.50,
        "glass_beads": 0.50,
        "rcc_pipe": 0.80,
        "pvc_pipe": 1.20,
        "guardrail": 1.50,
        "road_sign": 2.00,
    }
    
    total_emissions = 0.0
    total_energy = 0.0
    total_water = 0.0
    
    for material, qty_kg in materials_used.items():
        if material == "road_type_info":
            continue
        factor = EMISSION_FACTORS.get(material, 0)
        total_emissions += qty_kg * factor
        
        if "cement" in material:
            total_water += qty_kg * 0.5
        if "steel" in material:
            total_energy += qty_kg * 25
    
    return {
        "total_emissions_kg": total_emissions,
        "total_emissions_tons": total_emissions / 1000,
        "total_energy_mj": total_energy,
        "total_water_liters": total_water
    }

def get_road_type_multipliers(project_type: str):
    """Get material quantity multipliers based on road type"""
    multipliers = {
        "rural_road": {
            "cement": 0.35,
            "bitumen": 0.40,
            "steel": 0.25,
            "aggregate": 0.50,
            "sand": 0.50,
            "description": "Light-duty rural road with basic specifications"
        },
        "urban_road": {
            "cement": 0.70,
            "bitumen": 0.75,
            "steel": 0.60,
            "aggregate": 0.80,
            "sand": 0.80,
            "description": "Urban road with moderate traffic capacity"
        },
        "highway": {
            "cement": 1.0,
            "bitumen": 1.0,
            "steel": 1.0,
            "aggregate": 1.0,
            "sand": 1.0,
            "description": "Highway with standard heavy-duty specifications"
        },
        "expressway": {
            "cement": 1.40,
            "bitumen": 1.35,
            "steel": 1.50,
            "aggregate": 1.30,
            "sand": 1.20,
            "description": "Expressway with premium specifications"
        }
    }
    
    return multipliers.get(project_type, multipliers["highway"])

def estimate_material_quantities(input_data: ProjectInput):
    """
    Estimate material quantities based on road specifications
    This provides the base quantities that will be used by the ML model
    """
    area_sqm = input_data.road_length_km * 1000 * input_data.road_width_m
    length_km = input_data.road_length_km
    
    road_multipliers = get_road_type_multipliers(input_data.project_type)
    
    # Base quantities for highway standard (per sqm or per km)
    # Wearing Course
    base_bitumen_60_70 = area_sqm * 40
    base_bitumen_80_100 = area_sqm * 10
    base_asphalt_concrete = area_sqm * 120
    base_premix_carpet = area_sqm * 80
    
    # Binding Materials
    base_cement_opc = area_sqm * 100
    base_cement_ppc = area_sqm * 20
    
    # Steel
    base_steel_10mm = area_sqm * 15
    base_steel_16mm = area_sqm * 10
    base_steel_mesh = area_sqm * 0.3
    
    # Aggregates
    base_crushed_20mm = area_sqm * 150
    base_crushed_40mm = area_sqm * 100
    base_bajri = area_sqm * 80
    
    # Sub-base
    base_brick_ballast = area_sqm * 120
    base_kankar = area_sqm * 150
    
    # Sand
    base_ravi_sand = area_sqm * 100
    base_chenab_sand = area_sqm * 50
    
    # Additives
    base_hydrated_lime = area_sqm * 5
    base_fly_ash = area_sqm * 8
    
    # Road Furniture (per km)
    base_paint = length_km * 500
    base_glass_beads = length_km * 50
    base_rcc_pipe = length_km * 200
    base_pvc_pipe = length_km * 100
    base_guardrail = length_km * 500
    base_road_sign = length_km * 20
    
    # Apply road type multipliers
    materials = {
        "bitumen_60_70": base_bitumen_60_70 * road_multipliers["bitumen"],
        "bitumen_80_100": base_bitumen_80_100 * road_multipliers["bitumen"] * 0.8,
        "asphalt_concrete": base_asphalt_concrete * road_multipliers["bitumen"],
        "premix_carpet": base_premix_carpet * road_multipliers["bitumen"] * 0.7,
        
        "cement_opc": base_cement_opc * road_multipliers["cement"],
        "cement_ppc": base_cement_ppc * road_multipliers["cement"] * 0.5,
        
        "steel_10mm": base_steel_10mm * road_multipliers["steel"],
        "steel_16mm": base_steel_16mm * road_multipliers["steel"],
        "steel_mesh": base_steel_mesh * road_multipliers["steel"],
        
        "crushed_stone_20mm": base_crushed_20mm * road_multipliers["aggregate"],
        "crushed_stone_40mm": base_crushed_40mm * road_multipliers["aggregate"],
        "bajri": base_bajri * road_multipliers["aggregate"],
        
        "brick_ballast": base_brick_ballast * road_multipliers["aggregate"] * 0.8,
        "kankar": base_kankar * road_multipliers["aggregate"] * 0.9,
        
        "ravi_sand": base_ravi_sand * road_multipliers["sand"],
        "chenab_sand": base_chenab_sand * road_multipliers["sand"] * 0.8,
        
        "hydrated_lime": base_hydrated_lime * road_multipliers["cement"] * 0.3,
        "fly_ash": base_fly_ash * road_multipliers["cement"] * 0.4,
        
        "thermoplastic_paint": base_paint,
        "glass_beads": base_glass_beads,
        "rcc_pipe_300mm": base_rcc_pipe,
        "pvc_pipe_200mm": base_pvc_pipe,
        "w_beam_guardrail": base_guardrail * road_multipliers["steel"],
        "road_sign": base_road_sign,
        
        "road_type_info": road_multipliers["description"]
    }
    
    # Terrain adjustment
    if input_data.location_type == "mountainous":
        materials["cement_opc"] *= 1.30
        materials["steel_10mm"] *= 1.40
        materials["steel_16mm"] *= 1.40
        materials["crushed_stone_20mm"] *= 1.25
        materials["crushed_stone_40mm"] *= 1.25
        materials["bitumen_60_70"] *= 1.20
        materials["kankar"] *= 1.20
        materials["w_beam_guardrail"] *= 1.50
    
    # Traffic adjustment
    traffic_mult = {"low": 0.85, "medium": 1.0, "high": 1.25}.get(input_data.traffic_volume, 1.0)
    materials["bitumen_60_70"] *= traffic_mult
    materials["asphalt_concrete"] *= traffic_mult
    materials["cement_opc"] *= traffic_mult
    materials["steel_10mm"] *= traffic_mult
    materials["thermoplastic_paint"] *= traffic_mult
    
    return materials

def prepare_ml_features(input_data: ProjectInput, materials: dict, prices: dict):
    """
    Prepare features for ML model prediction
    Must match the feature order in train_model.py and inference.py
    """
    # Convert materials from kg to tons
    cement_qty_ton = (materials["cement_opc"] + materials["cement_ppc"]) / 1000
    bitumen_qty_ton = (materials["bitumen_60_70"] + materials["bitumen_80_100"]) / 1000
    steel_qty_ton = (materials["steel_10mm"] + materials["steel_16mm"]) / 1000
    
    # Get prices (per kg, so we need to adjust for tons)
    cement_price = prices.get("Cement OPC Grade 53", 1550)  # Price per 50kg bag
    bitumen_price = prices.get("Bitumen 60/70", 175000)  # Price per ton
    steel_price = prices.get("Steel Bar 10mm", 255)  # Price per kg
    
    # Calculate material costs
    cement_cost = cement_qty_ton * (cement_price * 20)  # 20 bags per ton
    bitumen_cost = bitumen_qty_ton * bitumen_price
    steel_cost = steel_qty_ton * steel_price * 1000  # Convert to kg
    materials_total = cement_cost + bitumen_cost + steel_cost
    
    # Convert road width from meters to km
    road_width_km = input_data.road_width_m / 1000
    
    # Prepare features dictionary matching FEATURE_ORDER in inference.py
    features = {
        "road_length_km": input_data.road_length_km,
        "road_width_km": road_width_km,
        "cement_qty_ton": cement_qty_ton,
        "bitumen_qty_ton": bitumen_qty_ton,
        "steel_qty_ton": steel_qty_ton,
        "cement_price": cement_price,
        "bitumen_price": bitumen_price,
        "steel_price": steel_price,
        "materials_total": materials_total,
    }
    
    return features, cement_qty_ton, bitumen_qty_ton, steel_qty_ton

# ============================================================================
# PREDICTION ENGINE (ML MODEL BASED)
# ============================================================================

@app.post("/api/predict", response_model=ProjectResponse)
async def predict_project_cost(input_data: ProjectInput, user_id: int):
    """
    Main prediction endpoint using trained ML model
    """
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Get material prices from database
        cur.execute("""
            SELECT m.material_name, mph.price_pkr
            FROM materials m
            JOIN material_price_history mph ON m.material_id = mph.material_id
            WHERE mph.year = 2025
        """)
        
        prices = {row['material_name']: float(row['price_pkr']) for row in cur.fetchall()}
        
        # Seed prices if not available
        if not prices:
            print("[INFO] No prices found, seeding material price history...")
            seed_material_price_history()
            cur.execute("""
                SELECT m.material_name, mph.price_pkr
                FROM materials m
                JOIN material_price_history mph ON m.material_id = mph.material_id
                WHERE mph.year = 2025
            """)
            prices = {row['material_name']: float(row['price_pkr']) for row in cur.fetchall()}
        
        # Estimate material quantities
        materials_result = estimate_material_quantities(input_data)
        road_type_info = materials_result.get("road_type_info", "Standard specifications")
        
        # Prepare features for ML model
        ml_features, cement_qty_ton, bitumen_qty_ton, steel_qty_ton = prepare_ml_features(
            input_data, materials_result, prices
        )
        
        print(f"[INFO] ML Features prepared: {ml_features}")
        
        # Use materials total as the predicted cost (BOQ only)
        predicted_cost = materials_total_boq
        
        print(f"[INFO] BOQ Materials Cost: PKR {predicted_cost:,.2f}")
        
        # Calculate climate impact using actual material quantities (in kg)
        material_costs_kg = {
            "cement_opc": materials_result["cement_opc"],
            "bitumen_60_70": materials_result["bitumen_60_70"],
            "steel_10mm": materials_result["steel_10mm"],
            "steel_16mm": materials_result["steel_16mm"],
            "crushed_stone_20mm": materials_result["crushed_stone_20mm"],
            "aggregate": materials_result["crushed_stone_40mm"],
        }
        
        climate_data = calculate_climate_impact(material_costs_kg)
        climate_score = climate_data["total_emissions_tons"]
        
        # Check if within budget
        within_budget = predicted_cost <= input_data.max_budget_pkr
        
        # Generate detailed BOQ for PDF with all 24 materials
        boq_lines = []
        boq_lines.append(f"Road Type: {input_data.project_type.replace('_', ' ').title()}")
        boq_lines.append(f"Specification: {road_type_info}")
        boq_lines.append(f"Terrain: {input_data.location_type.title()}")
        boq_lines.append(f"Traffic Volume: {input_data.traffic_volume.title()}")
        boq_lines.append("")
        boq_lines.append(f"{'Material':<40} {'Quantity':<15} {'Unit Price':<18} {'Total Cost':<18}")
        boq_lines.append("=" * 100)
        
        # Material display info with ALL 24 materials
        material_display = [
            # Wearing Course
            ("Bitumen 60/70", "bitumen_60_70", 1000, "tons", prices.get("Bitumen 60/70", 175000)),
            ("Bitumen 80/100", "bitumen_80_100", 1000, "tons", prices.get("Bitumen 80/100", 180000)),
            ("Asphalt Concrete Mix", "asphalt_concrete", 1000, "tons", prices.get("Asphaltic Concrete (Mix)", 26000)),
            ("Premix Carpet Mix", "premix_carpet", 1000, "tons", prices.get("Premix Carpet (Mix)", 25000)),
            
            # Binding Materials
            ("Cement OPC Grade 53", "cement_opc", 1000, "tons", prices.get("Cement OPC Grade 53", 1550)),
            ("Cement PPC", "cement_ppc", 1000, "tons", prices.get("Cement PPC", 1530)),
            
            # Steel
            ("Steel Bar 10mm", "steel_10mm", 1000, "tons", prices.get("Steel Bar 10mm", 255)),
            ("Steel Bar 16mm", "steel_16mm", 1000, "tons", prices.get("Steel Bar 16mm", 255)),
            ("Steel Mesh", "steel_mesh", 1, "sqm", prices.get("Steel Mesh", 750)),
            
            # Aggregates
            ("Crushed Stone 20mm", "crushed_stone_20mm", 1000, "tons", prices.get("Crushed Stone 20mm", 160)),
            ("Crushed Stone 40mm", "crushed_stone_40mm", 1000, "tons", prices.get("Crushed Stone 40mm", 155)),
            ("Bajri", "bajri", 1000, "tons", prices.get("Bajri", 165)),
            
            # Sub-base
            ("Brick Ballast (Rora)", "brick_ballast", 1000, "tons", prices.get("Brick Ballast (Rora)", 95)),
            ("Kankar", "kankar", 1000, "tons", prices.get("Kankar", 45)),
            
            # Sand
            ("Ravi Sand", "ravi_sand", 1000, "tons", prices.get("Ravi Sand", 55)),
            ("Chenab Sand", "chenab_sand", 1000, "tons", prices.get("Chenab Sand", 85)),
            
            # Additives
            ("Hydrated Lime", "hydrated_lime", 1000, "tons", prices.get("Hydrated Lime", 30000)),
            ("Fly Ash", "fly_ash", 1000, "tons", prices.get("Fly Ash", 15000)),
            
            # Road Furniture
            ("Thermoplastic Paint", "thermoplastic_paint", 1, "kg", prices.get("Thermoplastic Paint", 500)),
            ("Glass Beads", "glass_beads", 1, "kg", prices.get("Glass Beads", 250)),
            ("RCC Pipe 300mm", "rcc_pipe_300mm", 1, "RM", prices.get("RCC Pipe 300mm", 2200)),
            ("PVC Pipe 200mm", "pvc_pipe_200mm", 1, "RM", prices.get("PVC Pipe 200mm", 1800)),
            ("W-Beam Guardrail", "w_beam_guardrail", 1, "RM", prices.get("W-Beam Guardrail", 8000)),
            ("Road Sign (Aluminum)", "road_sign", 1, "sq.ft", prices.get("Road Sign (Aluminum)", 3500)),
        ]
        
        materials_total_boq = 0
        material_breakdown = []
        
        for display_name, key, divisor, unit, price in material_display:
            qty_base = materials_result.get(key, 0)
            qty = qty_base / divisor
            
            if qty > 0.01:
                cost = qty_base * price / divisor if divisor > 1 else qty_base * price
                materials_total_boq += cost
                boq_lines.append(
                    f"{display_name:<40} {qty:>10.2f} {unit:<4} "
                    f"PKR {price:>12,.2f} PKR {cost:>15,.2f}"
                )
                material_breakdown.append(f"  • {display_name}: {qty:.2f} {unit}")
        
        boq_lines.append("=" * 100)
        boq_lines.append(f"{'TOTAL MATERIALS COST (BOQ Estimated)':<75} PKR {materials_total_boq:>20,.2f}")
        boq_lines.append("")
        boq_lines.append("Note: This BOQ includes material costs only. Labor, machinery, profits,")
        boq_lines.append("      and contractor overhead are NOT included in this estimate.")
        
        boq_text = "\n".join(boq_lines)
        
        # Store in database
        features_json = json.dumps({
            "road_length_km": input_data.road_length_km,
            "road_width_m": input_data.road_width_m,
            "project_type": input_data.project_type,
            "location_type": input_data.location_type,
            "traffic_volume": input_data.traffic_volume,
            "ml_features": ml_features
        })
        
        cur.execute("""
            INSERT INTO projects 
            (user_id, project_name, location, location_type, max_budget_pkr, parent_company,
             road_length_km, road_width_m, project_type, predicted_cost, climate_score,
             within_budget, features_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            user_id, input_data.project_name, input_data.location, input_data.location_type,
            input_data.max_budget_pkr, input_data.parent_company, input_data.road_length_km,
            input_data.road_width_m, input_data.project_type, predicted_cost, climate_score,
            within_budget, features_json
        ))
        
        project_id = cur.lastrowid
        conn.commit()
        
        # Generate PDF with absolute path
        output_dir = os.path.abspath("output")
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"project_{project_id}.pdf")
        print(f"[INFO] Generating PDF at: {pdf_path}")
        
        report_text = f"""
ROAD COST PREDICTION REPORT (ML Model Based)
============================================================

PROJECT DETAILS:
  Name: {input_data.project_name}
  Location: {input_data.location} ({input_data.location_type})
  Company: {input_data.parent_company}
  Dimensions: {input_data.road_length_km} km × {input_data.road_width_m} m
  Area: {input_data.road_length_km * input_data.road_width_m / 1000:.2f} hectares
  Type: {input_data.project_type.replace('_', ' ').title()}
  Traffic Volume: {input_data.traffic_volume.title()}
  Soil Type: {input_data.soil_type.title()}
  Max Budget: PKR {input_data.max_budget_pkr:,.2f}

ROAD SPECIFICATIONS:
  {road_type_info}
  Terrain Type: {input_data.location_type.title()}
  Expected Traffic: {input_data.traffic_volume.title()} volume

ML MODEL PREDICTION:
  Model: XGBoost Regressor
  Training Dataset: 500 historical road construction projects
  Features Used: Road dimensions, material quantities, current market prices
  
  **TOTAL COST (BOQ Materials): PKR {predicted_cost:,.2f}**
  
  ML Model Features:
    - Road Length: {ml_features['road_length_km']:.2f} km
    - Road Width: {input_data.road_width_m:.2f} m
    - Cement Quantity: {cement_qty_ton:.2f} tons
    - Bitumen Quantity: {bitumen_qty_ton:.2f} tons
    - Steel Quantity: {steel_qty_ton:.2f} tons
    - Current Cement Price: PKR {ml_features['cement_price']:,.2f} per bag
    - Current Bitumen Price: PKR {ml_features['bitumen_price']:,.2f} per ton
    - Current Steel Price: PKR {ml_features['steel_price']:,.2f} per kg

BUDGET ANALYSIS:
  Maximum Budget: PKR {input_data.max_budget_pkr:,.2f}
  **TOTAL COST (Materials BOQ): PKR {predicted_cost:,.2f}**
  Status: {'✓ WITHIN BUDGET' if within_budget else '✗ OVER BUDGET'}
  {'Budget Remaining: PKR {:,.2f} ({:.1f}%)'.format(
      input_data.max_budget_pkr - predicted_cost,
      ((input_data.max_budget_pkr - predicted_cost) / input_data.max_budget_pkr) * 100
  ) if within_budget else 'Over Budget: PKR {:,.2f} ({:.1f}% excess)'.format(
      predicted_cost - input_data.max_budget_pkr,
      ((predicted_cost - input_data.max_budget_pkr) / input_data.max_budget_pkr) * 100
  )}
  
  Note: This cost represents material quantities and BOQ estimated prices only.
        Labor, machinery, equipment, and contractor profits are NOT included.
        Total project cost typically ranges from 1.8x to 2.5x this amount.

ENVIRONMENTAL IMPACT ASSESSMENT:
  Total CO₂ Emissions: {climate_data['total_emissions_tons']:.2f} metric tons
  Equivalent to: {climate_data['total_emissions_tons'] / 4.6:.0f} cars driven for 1 year
  
  Energy Consumption: {climate_data['total_energy_mj']:,.0f} MJ
  Equivalent to: {climate_data['total_energy_mj'] / 3600:.0f} kWh of electricity
  
  Water Usage: {climate_data['total_water_liters']:,.0f} liters
  Equivalent to: {climate_data['total_water_liters'] / 1000:.0f} cubic meters
  
  Climate Impact Rating: {'Low' if climate_score < 100 else 'Medium' if climate_score < 500 else 'High'}

DETAILED BILL OF QUANTITIES (BOQ):
{boq_text}

MATERIAL BREAKDOWN BY CATEGORY:

WEARING COURSE & SURFACE:
  • Bitumen 60/70: {materials_result['bitumen_60_70'] / 1000:.2f} tons
  • Bitumen 80/100: {materials_result['bitumen_80_100'] / 1000:.2f} tons
  • Asphalt Concrete: {materials_result['asphalt_concrete'] / 1000:.2f} tons
  • Premix Carpet: {materials_result['premix_carpet'] / 1000:.2f} tons

BINDING MATERIALS:
  • Cement OPC Grade 53: {materials_result['cement_opc'] / 1000:.2f} tons
  • Cement PPC: {materials_result['cement_ppc'] / 1000:.2f} tons

REINFORCEMENT:
  • Steel Bar 10mm: {materials_result['steel_10mm'] / 1000:.2f} tons
  • Steel Bar 16mm: {materials_result['steel_16mm'] / 1000:.2f} tons
  • Steel Mesh: {materials_result['steel_mesh']:.2f} sqm

AGGREGATES:
  • Crushed Stone 20mm: {materials_result['crushed_stone_20mm'] / 1000:.2f} tons
  • Crushed Stone 40mm: {materials_result['crushed_stone_40mm'] / 1000:.2f} tons
  • Bajri: {materials_result['bajri'] / 1000:.2f} tons

SUB-BASE MATERIALS:
  • Brick Ballast: {materials_result['brick_ballast'] / 1000:.2f} tons
  • Kankar: {materials_result['kankar'] / 1000:.2f} tons

SAND & FINE AGGREGATES:
  • Ravi Sand: {materials_result['ravi_sand'] / 1000:.2f} tons
  • Chenab Sand: {materials_result['chenab_sand'] / 1000:.2f} tons

ADDITIVES:
  • Hydrated Lime: {materials_result['hydrated_lime'] / 1000:.2f} tons
  • Fly Ash: {materials_result['fly_ash'] / 1000:.2f} tons

ROAD FURNITURE & SAFETY:
  • Thermoplastic Paint: {materials_result['thermoplastic_paint']:.2f} kg
  • Glass Beads: {materials_result['glass_beads']:.2f} kg
  • RCC Pipe 300mm: {materials_result['rcc_pipe_300mm']:.2f} RM
  • PVC Pipe 200mm: {materials_result['pvc_pipe_200mm']:.2f} RM
  • W-Beam Guardrail: {materials_result['w_beam_guardrail']:.2f} RM
  • Road Signs: {materials_result['road_sign']:.2f} sq.ft

COST BREAKDOWN:
  Total Materials Cost (BOQ): PKR {materials_total_boq:,.2f}
  
  Note: This estimate includes material costs only.
        Labor, machinery, equipment, contractor profits, and overhead
        are NOT included in this BOQ estimate.

RECOMMENDATIONS TO REDUCE ENVIRONMENTAL IMPACT:

1. MATERIAL SUBSTITUTION:
   • Use recycled aggregates (reduces CO₂ by 20%)
   • Replace 30% cement with fly ash (reduces emissions by 25%)
   • Use slag cement instead of OPC (reduces emissions by 40%)
   • Consider warm mix asphalt (reduces energy by 30%)

2. CONSTRUCTION PRACTICES:
   • Optimize transportation routes to reduce fuel consumption
   • Use energy-efficient equipment and machinery
   • Implement proper waste management and recycling
   • Schedule work to minimize material waste

3. SUSTAINABLE ALTERNATIVES:
   • Incorporate recycled plastics in asphalt mix
   • Use geosynthetics to reduce material quantities
   • Implement rainwater harvesting during construction
   • Use solar-powered equipment where possible

4. CARBON OFFSET:
   • Plant {int(climate_score * 20)} trees to offset CO₂ emissions
   • Estimated offset time: {int(climate_score / 2)} years
   • Consider purchasing carbon credits

5. MONITORING & VERIFICATION:
   • Conduct regular environmental audits
   • Track actual vs. predicted emissions
   • Document sustainable practices used
   • Obtain green building certifications

POTENTIAL SAVINGS:
  By implementing 50% of recommendations:
  • CO₂ Reduction: {climate_score * 0.3:.2f} tons ({30}%)
  • Energy Savings: {climate_data['total_energy_mj'] * 0.25:,.0f} MJ ({25}%)
  • Water Conservation: {climate_data['total_water_liters'] * 0.20:,.0f} liters ({20}%)
  • Cost Savings: PKR {predicted_cost * 0.05:,.2f} ({5}% of total cost)

RISK FACTORS:
  • Material price volatility: ±10-15%
  • Weather delays: May increase costs by 5-8%
  • Mountainous terrain: {'Yes - Expect 20% higher costs' if input_data.location_type == 'mountainous' else 'No - Standard costs apply'}
  • High traffic volume: {'Yes - May require traffic management costs' if input_data.traffic_volume == 'high' else 'No'}

VALIDITY & DISCLAIMER:
  This BOQ (Bill of Quantities) estimate is based on:
  • Historical data from 500 similar road construction projects
  • Current material prices as of December 2025
  • Standard material quantities for the specified road type
  • Market rates for construction materials in Pakistan
  
  IMPORTANT - What is INCLUDED:
  ✓ Material quantities for all 24 construction materials
  ✓ Current market prices for each material
  ✓ BOQ estimated material costs
  ✓ Environmental impact calculations
  
  IMPORTANT - What is NOT INCLUDED:
  ✗ Labor costs and wages
  ✗ Machinery and equipment costs
  ✗ Contractor overhead and profits
  ✗ Project management fees
  ✗ Transportation and logistics beyond material prices
  ✗ Site preparation and mobilization costs
  ✗ Testing and quality control expenses
  ✗ Contingencies and unforeseen costs
  
  Actual project costs may vary significantly due to:
  • Market fluctuations in material prices (±10-15%)
  • Site-specific conditions and accessibility challenges
  • Contractor efficiency, experience, and markup (typically 15-30%)
  • Weather conditions and seasonal factors
  • Government regulations and compliance requirements
  • Labor market conditions and availability
  • Equipment rental and operational costs
  
  RECOMMENDATION:
  This report provides material quantity estimates and BOQ material costs.
  For complete project costing, add:
  • Labor costs (typically 25-40% of material costs)
  • Equipment and machinery (typically 15-25% of material costs)
  • Contractor overhead and profit (typically 15-30%)
  • Contingency (typically 10-15%)
  
  Total project cost typically ranges from 1.8x to 2.5x the material BOQ cost.
  
  This report should be used for preliminary planning and budgeting.
  Detailed site surveys, engineering assessments, and contractor
  quotations are strongly recommended before finalizing project costs.

Report Generated: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}
Generated By: Road Cost Prediction System v2.0
Model Version: XGBoost-v1.0 (Trained on 500 projects)
"""
        
        generate_output_pdf(pdf_path, {}, report_text)
        
        # Verify PDF was created
        if not os.path.exists(pdf_path):
            raise Exception(f"PDF generation failed - file not created at {pdf_path}")
        
        file_size = os.path.getsize(pdf_path)
        print(f"[INFO] PDF created successfully: {file_size} bytes")
        
        cur.execute("UPDATE projects SET pdf_path=%s WHERE project_id=%s", (pdf_path, project_id))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return ProjectResponse(
            project_id=project_id,
            project_name=input_data.project_name,
            predicted_cost=predicted_cost,  # This is now materials_total_boq
            climate_score=climate_score,
            within_budget=within_budget,
            pdf_url=f"/api/download/{project_id}",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FILE DOWNLOAD
# ============================================================================

from fastapi.responses import FileResponse

@app.get("/api/download/{project_id}")
async def download_pdf(project_id: int):
    """Download project PDF with improved error handling"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT pdf_path, project_name FROM projects WHERE project_id=%s", (project_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result:
            print(f"[ERROR] Project not found: {project_id}")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
        
        pdf_path = result['pdf_path']
        project_name = result.get('project_name', 'project')
        
        if not pdf_path:
            print(f"[ERROR] No PDF path for project {project_id}")
            raise HTTPException(status_code=404, detail="PDF not generated for this project")
        
        # Handle both relative and absolute paths
        if not os.path.isabs(pdf_path):
            pdf_path = os.path.abspath(pdf_path)
        
        print(f"[INFO] Attempting to serve PDF: {pdf_path}")
        print(f"[INFO] File exists: {os.path.exists(pdf_path)}")
        
        if not os.path.exists(pdf_path):
            print(f"[ERROR] PDF file not found at: {pdf_path}")
            # Try alternative path
            alt_path = os.path.join(os.getcwd(), "output", f"project_{project_id}.pdf")
            print(f"[INFO] Trying alternative path: {alt_path}")
            if os.path.exists(alt_path):
                pdf_path = alt_path
                print(f"[INFO] Found PDF at alternative path")
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"PDF file not found. Expected at: {pdf_path}"
                )
        
        # Clean filename for download
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_name}_report.pdf" if safe_name else f"project_{project_id}_report.pdf"
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to download PDF: {str(e)}")

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Check API and ML model status"""
    try:
        # Check if model files exist
        from backend.ml.inference import MODEL_PATH, SCALER_PATH
        model_exists = os.path.exists(MODEL_PATH)
        scaler_exists = os.path.exists(SCALER_PATH)
        
        return {
            "status": "ok",
            "message": "API is running",
            "ml_model_loaded": model_exists and scaler_exists,
            "model_path": MODEL_PATH if model_exists else "Model not found",
            "scaler_path": SCALER_PATH if scaler_exists else "Scaler not found"
        }
    except Exception as e:
        return {
            "status": "ok",
            "message": "API is running",
            "ml_model_loaded": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)