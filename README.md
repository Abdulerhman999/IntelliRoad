# IntelliRoad - AI-Powered Road Cost Predictor

IntelliRoad is a machine learning-based application designed to predict road construction costs based on project parameters like location, terrain, and materials. It features a React frontend and a FastAPI backend with MySQL integration

## Getting Started

Follow these steps to set up the project on your local machine.

### Prerequisites
Before you begin, ensure you have the following installed:
- **MySQL Server** (Make sure it is running)
- **Git**

### Installation Guide

#### 1. Database Configuration
You need to set up the MySQL database manually.
1. Open your MySQL tool (Workbench, HeidiSQL, or Command Line).
2. Open and run the script located at:
   `sql/schema.sql`
   *(This creates the `ml_db` database and necessary tables).*

#### 2. Update Configuration
Connect the application to your database.
1. Open the **`config.yaml`** file in the root directory.
2. Find the `mysql` section.
3. Replace the password field with your actual MySQL root password:
   ```yaml
   mysql:
     host: "localhost"
     user: "root"
     password: "YOUR_REAL_PASSWORD_HERE"  <-- Change this
     db: "ml_db"

#### 3. Automated Setup
We have included a one-click installer to handle dependencies and environment setup.
1. Double-click the **`INSTALL.bat`** file in the root directory.
2. Wait for the process to complete (this will install Python libraries, Node.js packages, and set up the virtual environment).