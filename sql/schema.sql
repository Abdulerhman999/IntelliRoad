-- -------------------------------------------------------------
--  USERS AND PROJECTS TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    user_id           INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(255) NOT NULL,
    email             VARCHAR(255) NOT NULL UNIQUE,
    phone             VARCHAR(50),
    username          VARCHAR(100) NOT NULL UNIQUE,
    password_hash     VARCHAR(255) NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS projects (
    project_id        INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NOT NULL,
    project_name      VARCHAR(255) NOT NULL,
    location          VARCHAR(255),
    location_type     VARCHAR(50),  -- 'plain' or 'mountainous'
    max_budget_pkr    DOUBLE,
    parent_company    VARCHAR(255),
    road_length_km    DOUBLE,
    road_width_m      DOUBLE,
    project_type      VARCHAR(100), -- 'highway', 'urban_road', 'rural_road'
    soil_type         VARCHAR(50),
    traffic_volume    VARCHAR(50),
    predicted_cost    DOUBLE,
    climate_score     DOUBLE,
    within_budget     BOOLEAN,
    features_json     JSON,
    pdf_path          TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
-- -------------------------------------------------------------
--  CORE PROJECT TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenders (
    tender_id           INT AUTO_INCREMENT PRIMARY KEY,
    source_site         VARCHAR(255),
    tender_url          TEXT,
    tender_no           VARCHAR(255),
    title               TEXT,
    department          VARCHAR(255),
    city                VARCHAR(255),
    province            VARCHAR(255),
    publish_date        DATE,
    closing_date        DATE,
    category                VARCHAR(255),
    procurement_method      VARCHAR(255),
    opening_date            DATE,
    status                  VARCHAR(100),
    organization            VARCHAR(255),
    raw_pdf_path        TEXT,
    cleaned_pdf_path    TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boq_files (
    boq_id            INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    file_path         TEXT,
    extracted_text    LONGTEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id)
);

CREATE TABLE IF NOT EXISTS boq_items (
    item_id           INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    boq_id            INT,
    item_code         VARCHAR(255),
    description       TEXT,
    unit              VARCHAR(50),
    quantity          DOUBLE,
    rate              DOUBLE,
    cost              DOUBLE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id),
    FOREIGN KEY (boq_id) REFERENCES boq_files(boq_id)
);

-- -------------------------------------------------------------
--  MATERIAL + PRICE TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS materials (
    material_id       INT AUTO_INCREMENT PRIMARY KEY,
    material_name     VARCHAR(255) UNIQUE,
    unit              VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS material_price_raw (
    raw_id            INT AUTO_INCREMENT PRIMARY KEY,
    material_name     VARCHAR(255),
    canonical_material_id INT,
    unit              VARCHAR(50),
    price_pkr         DOUBLE,
    year              INT,
    source            VARCHAR(255),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (canonical_material_id) REFERENCES materials(material_id)
);

CREATE TABLE IF NOT EXISTS material_price_history (
    mph_id            INT AUTO_INCREMENT PRIMARY KEY,
    material_id       INT,
    year              INT,
    price_pkr         DOUBLE,
    unit              VARCHAR(50),
    effective_date    DATE,
    UNIQUE(material_id, year),
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
);

CREATE TABLE IF NOT EXISTS material_inflation_index (
    mii_id            INT AUTO_INCREMENT PRIMARY KEY,
    material_id       INT,
    year              INT,
    inflation_rate    DOUBLE,
    UNIQUE(material_id, year),
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
);

-- -------------------------------------------------------------
--  MODEL TRAINING TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS model_training_runs (
    run_id              INT AUTO_INCREMENT PRIMARY KEY,
    model_path          TEXT,
    scaler_path         TEXT,
    training_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    num_records         INT,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS features_cache (
    feature_id        INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    features_json     JSON,
    target_cost       DOUBLE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id)
);
CREATE TABLE IF NOT EXISTS ml_training_data (
    training_id       INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    features_json     JSON,
    label_cost        DOUBLE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_id),
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id)
);

-- -------------------------------------------------------------
--  PREDICTIONS + OUTPUT STORAGE
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id     INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    model_run_id      INT,
    predicted_cost    DOUBLE,
    climate_score     DOUBLE,
    output_pdf_path   TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id),
    FOREIGN KEY (model_run_id) REFERENCES model_training_runs(run_id)
);

-- -------------------------------------------------------------
--  CLIMATE IMPACT TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS climate_factors (
    factor_id         INT AUTO_INCREMENT PRIMARY KEY,
    material_id       INT,
    emission_factor   DOUBLE,
    water_factor      DOUBLE,
    energy_factor     DOUBLE,
    notes             TEXT,
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
);

CREATE TABLE IF NOT EXISTS climate_results (
    clim_id           INT AUTO_INCREMENT PRIMARY KEY,
    tender_id         INT,
    total_emissions   DOUBLE,
    total_energy      DOUBLE,
    total_water       DOUBLE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(tender_id)
);

-- -------------------------------------------------------------
--  LOGGING TABLES
-- -------------------------------------------------------------

CREATE TABLE IF NOT EXISTS scraper_logs (
    log_id            INT AUTO_INCREMENT PRIMARY KEY,
    tender_url        TEXT,
    status            VARCHAR(50),
    message           TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parser_logs (
    log_id            INT AUTO_INCREMENT PRIMARY KEY,
    boq_id            INT,
    message           TEXT,
    severity          VARCHAR(50),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boq_id) REFERENCES boq_files(boq_id)
);