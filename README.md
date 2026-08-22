<div align="center">

<!-- Animated typing banner -->
<a href="https://github.com/viRAJ357/Revenue-AI-Tracker">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=800&size=34&duration=3000&pause=1000&color=F86666&center=true&vCenter=true&width=860&lines=Revenue+AI+Tracker;AI-Powered+Revenue+Forecasting;Data+Ingestion+to+Deployment;End-to-End+Machine+Learning+Pipeline!" alt="Typing SVG" />
</a>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=header&text=Revenue%20AI%20Tracker&fontSize=42&fontColor=fff&animation=twinkling&fontAlignY=40" width="100%"/>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white"/>
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white"/>
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>

<h3>An end-to-end AI-powered system to predict, track, and visualize business revenue — from raw data ingestion to live dashboard deployment.</h3>

<br/>

<a href="index.html">
  <img src="https://img.shields.io/badge/Open_3D_Interactive_Flow_Graph-1f6feb?style=for-the-badge&logo=threedotjs&logoColor=white" alt="3D Graph"/>
</a>

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🎬 Motion Animation — Live Data Pipeline Flow

> Built from scratch using pure **Python + Pillow**. Visualizes the entire 10-step Revenue AI pipeline flowing in real time!

<div align="center">
  <img src="assets/flow_animation.gif" alt="Revenue AI Tracker Animated Flow" width="100%"/>
</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🌟 Full Architecture — 3D Interactive Graph

> Open `index.html` locally in any browser to explore the **advanced n8n-style 3D rotating graph** with particle flows connecting every step!

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#0d1117','primaryTextColor':'#c9d1d9','primaryBorderColor':'#3fb950','lineColor':'#58a6ff','secondaryColor':'#161b22','tertiaryColor':'#2ea043'}}}%%
graph TD
    classDef root   fill:#f86666,stroke:#fff,stroke-width:3px,color:#000;
    classDef setup  fill:#1a2b42,stroke:#58a6ff,stroke-width:2px,color:#c9d1d9;
    classDef data   fill:#0f2a2a,stroke:#3fb9b4,stroke-width:2px,color:#c9d1d9;
    classDef ml     fill:#2a2200,stroke:#e5c059,stroke-width:2px,color:#c9d1d9;
    classDef api    fill:#2a0f0f,stroke:#f86666,stroke-width:2px,color:#c9d1d9;
    classDef viz    fill:#1e1235,stroke:#bc8cff,stroke-width:2px,color:#c9d1d9;

    ROOT(("Revenue AI Tracker")):::root --> S01

    subgraph Phase1 [Setup]
      S01(Step 01: Project Setup & Config):::setup
    end

    subgraph Phase2 [Data Engineering]
      S02(Step 02: Data Ingestion):::data
      S03(Step 03: Preprocessing & Cleaning):::data
      S04(Step 04: Exploratory Data Analysis):::data
    end

    subgraph Phase3 [AI / ML]
      S05(Step 05: Feature Engineering):::ml
      S06(Step 06: AI Model Training):::ml
      S07(Step 07: Model Evaluation & Tuning):::ml
    end

    subgraph Phase4 [API & Viz]
      S08(Step 08: Revenue Prediction API):::api
      S09(Step 09: Dashboard & Visualization):::viz
    end

    subgraph Phase5 [DevOps]
      S10(Step 10: Deployment & Monitoring):::api
    end

    S01 --> S02 --> S03 --> S04 --> S05 --> S06 --> S07 --> S08 --> S09 --> S10
    S04 --> S06
    S07 --> S09
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 📂 Step-by-Step Breakdown

### 🔵 Phase 1 — Project Setup
- **`Step_01_Project_Overview_and_Setup/`**
  Environment setup, project configuration, dependency installation. Sets up Python virtual environments, installs required libraries (`pandas`, `sklearn`, `fastapi`, `plotly`), and defines the project configuration schema.

---

### 🟦 Phase 2 — Data Engineering

- **`Step_02_Data_Collection_and_Ingestion/`**
  Handles loading revenue data from CSV, databases, or APIs. Sets up ingestion pipelines and data validation checks to ensure data quality from the start.

- **`Step_03_Data_Preprocessing_and_Cleaning/`**
  Handles missing values, outlier detection, data type normalization, and feature scaling. Transforms raw, noisy data into a clean, structured format ready for analysis.

- **`Step_04_Exploratory_Data_Analysis/`**
  Deep statistical analysis using Pandas and Plotly. Generates correlation matrices, revenue trend charts, seasonal decomposition plots, and business KPI summaries.

---

### 🟡 Phase 3 — AI / Machine Learning

- **`Step_05_Feature_Engineering/`**
  Builds predictive features: lag features (revenue from past N months), rolling averages, seasonality flags, and external economic indicators.

- **`Step_06_AI_Model_Training/`**
  Trains multiple regression models: Linear Regression, Random Forest, XGBoost, and a stacked ensemble. Saves model artifacts using `joblib`.

- **`Step_07_Model_Evaluation_and_Tuning/`**
  Evaluates models using MAE, RMSE, R² metrics. Uses `GridSearchCV` and `RandomizedSearchCV` for hyperparameter tuning. Selects the best-performing model.

---

### 🔴 Phase 4 — API & Visualization

- **`Step_08_Revenue_Prediction_API/`**
  Serves the trained model as a REST API using **FastAPI**. Accepts business input features and returns revenue predictions with confidence intervals. Includes `/docs` Swagger UI.

- **`Step_09_Dashboard_and_Visualization/`**
  Interactive **Plotly Dash** dashboard displaying real-time revenue forecasts, trend analysis charts, model performance metrics, and business alerts.

---

### 🐳 Phase 5 — Deployment

- **`Step_10_Deployment_and_Monitoring/`**
  Containerizes the full stack (API + Dashboard) using **Docker** and `docker-compose`. Includes monitoring setup, health checks, and production deployment guides.

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/viRAJ357/Revenue-AI-Tracker.git
cd Revenue-AI-Tracker
```

### 2. View the 3D Graph
Double-click **`index.html`** in any browser — experience the n8n-style rotating 3D flow graph!

### 3. Run the Revenue Prediction API
```bash
cd Step_08_Revenue_Prediction_API
pip install fastapi uvicorn scikit-learn pandas
uvicorn main:app --reload
```
Visit `http://127.0.0.1:8000/docs` for interactive Swagger UI.

### 4. Run via Docker
```bash
docker-compose up --build
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Data Processing | Pandas, NumPy |
| Machine Learning | scikit-learn, XGBoost |
| API | FastAPI + Uvicorn |
| Visualization | Plotly, Dash |
| Containerization | Docker, docker-compose |
| 3D Graph | 3d-force-graph.js |
| Animation | Python Pillow (custom) |

<div align="center">
  <br/>
  <i>Built with AI, motion, and Python — end to end.</i>
  <br/><br/>
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>
</div>
