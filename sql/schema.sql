-- 1. USERS TABLE (Admin and Employees)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'employee') NOT NULL DEFAULT 'employee',
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

-- 2. MATERIALS CATEGORY & MATERIALS
-- ============================================================================
CREATE TABLE IF NOT EXISTS material_categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    display_order INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS materials (
    material_id INT PRIMARY KEY AUTO_INCREMENT,
    material_name VARCHAR(255) UNIQUE NOT NULL,
    unit VARCHAR(50) NOT NULL,
    category_id INT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES material_categories(category_id) ON DELETE SET NULL
);

-- 3. MATERIAL PRICES (Current Prices - Editable by Admin)
-- ============================================================================
CREATE TABLE IF NOT EXISTS material_prices (
    price_id INT PRIMARY KEY AUTO_INCREMENT,
    material_id INT NOT NULL,
    price_2023 DOUBLE NOT NULL DEFAULT 0,
    price_2024 DOUBLE NOT NULL DEFAULT 0,
    price_current DOUBLE NOT NULL DEFAULT 0,
    unit VARCHAR(50) NOT NULL,
    last_updated_by INT,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE CASCADE,
    FOREIGN KEY (last_updated_by) REFERENCES users(user_id) ON DELETE SET NULL,
    UNIQUE KEY unique_material_price (material_id)
);

-- 4. MATERIAL CLIMATIC IMPACT (Emission Factors)
-- ============================================================================
CREATE TABLE IF NOT EXISTS material_climatic_impact (
    impact_id INT PRIMARY KEY AUTO_INCREMENT,
    material_id INT NOT NULL,
    emission_factor_kg_co2_per_kg DOUBLE NOT NULL,
    energy_consumption_mj DOUBLE DEFAULT 0,
    water_usage_liters DOUBLE DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE CASCADE,
    UNIQUE KEY unique_material_impact (material_id)
);

-- 5. PROJECTS TABLE (Main Project Information)
-- ============================================================================
CREATE TABLE IF NOT EXISTS projects (
    project_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    location_type ENUM('plain', 'mountainous') NOT NULL DEFAULT 'plain',
    parent_company VARCHAR(255) NOT NULL,
    road_length_km DOUBLE NOT NULL,
    road_width_m DOUBLE NOT NULL,
    area_hectares DOUBLE,
    project_type ENUM('highway', 'urban_road', 'rural_road', 'expressway') NOT NULL,
    traffic_volume ENUM('low', 'medium', 'high') DEFAULT 'medium',
    soil_type ENUM('normal', 'sandy', 'clayey', 'rocky') DEFAULT 'normal',
    max_budget_pkr DOUBLE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_location_type (location_type),
    INDEX idx_created_at (created_at)
);

-- 6. PROJECT PREDICTIONS (ML Model Predictions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_predictions (
    prediction_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    predicted_cost_pkr DOUBLE NOT NULL,
    total_co2_emissions_tons DOUBLE NOT NULL,
    total_energy_mj DOUBLE DEFAULT 0,
    total_water_liters DOUBLE DEFAULT 0,
    budget_status ENUM('Within Budget', 'Over Budget') NOT NULL,
    budget_difference_pkr DOUBLE,
    budget_utilization_percent DOUBLE,
    model_version VARCHAR(50),
    features_json JSON,
    pdf_report_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    UNIQUE KEY unique_project_prediction (project_id)
);

-- 7. PROJECT BOQ (Bill of Quantities)
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_boq (
    boq_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    material_id INT NOT NULL,
    quantity DOUBLE NOT NULL,
    unit VARCHAR(50) NOT NULL,
    unit_price_pkr DOUBLE NOT NULL,
    total_cost_pkr DOUBLE NOT NULL,
    category_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE RESTRICT,
    INDEX idx_project_id (project_id)
);

-- 8. PROJECT CLIMATE IMPACT (Detailed Climate Calculations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_climate_impact (
    climate_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    material_id INT NOT NULL,
    quantity_kg DOUBLE NOT NULL,
    co2_emissions_kg DOUBLE NOT NULL,
    energy_consumption_mj DOUBLE DEFAULT 0,
    water_usage_liters DOUBLE DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE RESTRICT,
    INDEX idx_project_id (project_id)
);

-- 9. CLIMATE REDUCTION RECOMMENDATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS climate_recommendations (
    recommendation_id INT PRIMARY KEY AUTO_INCREMENT,
    group_name VARCHAR(255) NOT NULL,
    recommendation_text TEXT NOT NULL,
    potential_reduction_percent DOUBLE,
    applicability VARCHAR(255),
    priority ENUM('High', 'Medium', 'Low') DEFAULT 'Medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. TENDERS (Historical Data for ML Training)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenders (
    tender_id INT PRIMARY KEY AUTO_INCREMENT,
    tender_no VARCHAR(100) UNIQUE,
    title TEXT,
    organization VARCHAR(255),
    project_name VARCHAR(255),
    location VARCHAR(255),
    location_type ENUM('plain', 'mountainous'),
    parent_company VARCHAR(255),
    road_length_km DOUBLE,
    road_width_m DOUBLE,
    project_type ENUM('highway', 'urban_road', 'rural_road', 'expressway'),
    traffic_volume ENUM('low', 'medium', 'high'),
    soil_type ENUM('normal', 'sandy', 'clayey', 'rocky'),
    actual_cost_pkr DOUBLE,
    boq_json JSON,
    used_for_training BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_used_for_training (used_for_training)
);

-- 11. ML TRAINING DATA
-- ============================================================================
CREATE TABLE IF NOT EXISTS ml_training_data (
    training_id INT PRIMARY KEY AUTO_INCREMENT,
    tender_id INT NOT NULL,
    features_json JSON NOT NULL,
    label_cost_pkr DOUBLE NOT NULL,
    data_quality ENUM('High', 'Medium', 'Low') DEFAULT 'Medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id) ON DELETE CASCADE,
    UNIQUE KEY unique_tender_training (tender_id)
);
CREATE TABLE IF NOT EXISTS model_training_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    status VARCHAR(50) NOT NULL,  -- in_progress, completed, failed
    training_data_count INT NOT NULL,
    model_version VARCHAR(100),
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    log_output TEXT,
    error_message TEXT,
    FOREIGN KEY (admin_id) REFERENCES users(user_id)
);

INSERT INTO users (
    user_id, name, email, phone, username, password_hash, role
)
SELECT
    1,
    'System Administrator',
    'admin@roadcost.com',
    NULL,
    'admin',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
    'admin'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'admin'
);
