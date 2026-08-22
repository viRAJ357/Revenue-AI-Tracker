<div align="center">

<!-- Animated typing banner -->
<a href="https://github.com/viRAJ357/Revenue-AI-Tracker">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=800&size=34&duration=3000&pause=1000&color=F86666&center=true&vCenter=true&width=860&lines=Revenue+AI+Tracker;RecoverAI+-+Intelligent+Payment+Recovery;CatBoost+ML+Powered+System;Failed+Transaction+to+Recovered+Revenue!" alt="Typing SVG" />
</a>

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=120&section=header&text=RecoverAI%20%E2%80%94%20Revenue%20AI%20Tracker&fontSize=36&fontColor=fff&animation=twinkling&fontAlignY=42" width="100%"/>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white"/></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-API_Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white"/></a>
  <a href="https://catboost.ai"><img src="https://img.shields.io/badge/CatBoost-ML_Engine-FFCC00?style=for-the-badge&logo=yandex&logoColor=black"/></a>
  <img src="https://img.shields.io/badge/Plotly-Dashboard-3F4F75?style=for-the-badge&logo=plotly&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Deployment-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/></a>
</p>

<h3>An end-to-end AI system that predicts whether a failed financial transaction can be recovered — using CatBoost ML, FastAPI, and a live Operator Dashboard.</h3>

<br/>

<a href="index.html">
  <img src="https://img.shields.io/badge/Open_3D_Interactive_Flow_Graph-1f6feb?style=for-the-badge&logo=threedotjs&logoColor=white" alt="3D Graph"/>
</a>

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🎬 Motion Animation — Live Pipeline Flow

> Built from scratch using pure **Python + Pillow** — shows the full 10-step RecoverAI data pipeline animating in real time!

<div align="center">
  <img src="assets/flow_animation.gif" alt="Revenue AI Tracker Animated Pipeline Flow" width="100%"/>
</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 📌 Table of Contents

- [Problem Statement](#-problem-statement)
- [System Architecture](#-system-architecture)
- [3D Interactive Flow Graph](#-3d-interactive-flow-graph)
- [Project Features](#-project-features)
- [ML Pipeline Workflow](#-ml-pipeline-workflow)
- [Project Structure](#-project-structure)
- [Quick Start Guide](#-quick-start-guide)
- [API Endpoints](#-api-endpoints)

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%">

## 🎯 Problem Statement

Every day, **millions of financial transactions fail** due to network errors, insufficient funds, or timeouts. Knowing exactly which transactions have a high probability of recovery can save businesses millions in lost revenue.

**RecoverAI** tackles this by predicting the likelihood of a transaction being successfully recovered within 72 hours, offering actionable recommendations like `Smart Retry`, `Delayed Retry`, or `Human Review`.

---

## 🏗️ System Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#0d1117','primaryTextColor':'#c9d1d9','primaryBorderColor':'#3fb950','lineColor':'#58a6ff','secondaryColor':'#161b22'}}}%%
flowchart TD
    classDef ui   fill:#1a2b42,stroke:#58a6ff,stroke-width:2px,color:#c9d1d9;
    classDef api  fill:#2a2200,stroke:#e5c059,stroke-width:2px,color:#c9d1d9;
    classDef core fill:#2a0f0f,stroke:#f86666,stroke-width:2px,color:#c9d1d9;
    classDef db   fill:#0f2a2a,stroke:#3fb9b4,stroke-width:2px,color:#c9d1d9;

    UI["Frontend\n(HTML/CSS/JS)"]:::ui <-->|HTTP/REST| API["FastAPI Backend\n(main.py | Port 8000)"]:::api

    API -->|PaymentEvent JSON| GR["Guardrail Layer\n(5 Rules)"]:::core

    GR -->|Passes| ML["CatBoost Policy Engine\n(*.cbm model)"]:::core
    GR -.->|Fails| Forced["Forced Action\n(e.g. human_review)"]:::core

    ML -->|RecoveryDecision| DB[("SQLite Audit DB\n(database.py)")]:::db
    Forced --> DB
```

## 📥 Input & 📤 Output Details

**Input (PaymentEvent JSON):** The API accepts a payload detailing the failed transaction — amount, merchant, customer history, previous failures, and device data.

**Output (RecoveryDecision):** The API responds with the recommended action (`smart_retry`, `human_review`, etc.), confidence probability (0.0–1.0), and guardrail flags.

---

## 🌀 3D Interactive Flow Graph

> Clone the repo and open **`index.html`** locally to experience the **n8n-style rotating 3D particle flow graph** connecting all pipeline nodes!

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#0d1117','primaryTextColor':'#c9d1d9','primaryBorderColor':'#f86666','lineColor':'#f86666'}}}%%
graph TD
    classDef setup  fill:#1a2b42,stroke:#58a6ff,stroke-width:2px,color:#c9d1d9;
    classDef data   fill:#0f2a2a,stroke:#3fb9b4,stroke-width:2px,color:#c9d1d9;
    classDef ml     fill:#2a2200,stroke:#e5c059,stroke-width:2px,color:#c9d1d9;
    classDef api    fill:#2a0f0f,stroke:#f86666,stroke-width:2px,color:#c9d1d9;
    classDef viz    fill:#1e1235,stroke:#bc8cff,stroke-width:2px,color:#c9d1d9;

    S01(Step 01: Project Setup):::setup --> S02
    S02(Step 02: Data Ingestion):::data --> S03
    S03(Step 03: Preprocessing):::data --> S04
    S04(Step 04: EDA):::data --> S05
    S05(Step 05: Feature Engineering):::ml --> S06
    S06(Step 06: AI Model Training):::ml --> S07
    S07(Step 07: Model Evaluation):::ml --> S08
    S08(Step 08: Revenue Prediction API):::api --> S09
    S09(Step 09: Dashboard):::viz --> S10
    S10(Step 10: Deployment):::api

    S04 --> S06
    S07 --> S09
```

---

## ✨ Project Features

### 💻 Operator Dashboard (Frontend)
- Real-time monitoring of failed transactions.
- Beautiful, responsive UI to review "Human Review" cases.
- Analytics and graphs tracking recovery rates.

### 🛡️ Guardrail Engine & API
- **FastAPI** backend exposing REST endpoints for transaction processing.
- A **Guardrail Layer** that forces manual review for high-value or high-risk transactions before hitting the ML model.

### 🧠 Machine Learning Engine
- Uses **CatBoostClassifier** — natively handles categorical features without manual one-hot encoding.
- Incorporates early stopping with AUC-optimised evaluation.

---

## 🔬 ML Pipeline Workflow

```mermaid
graph TD
    classDef file    fill:#2a2200,stroke:#e5c059,stroke-width:2px,color:#c9d1d9;
    classDef process fill:#0f2a2a,stroke:#3fb9b4,stroke-width:2px,color:#c9d1d9;
    classDef output  fill:#172a1e,stroke:#3fb950,stroke-width:2px,color:#c9d1d9;

    subgraph Phase1 [Phase 1: Data Gathering]
        DL["download_datasets.py"]:::process -->|Downloads| Kaggle["Raw Kaggle CSVs\n(PaySim, etc.)"]:::file
    end

    subgraph Phase2 [Phase 2: Feature Engineering]
        Kaggle --> Build["build_recoverai_dataset.py\nEngineers 26 Features"]:::process
        Build --> TrainCSV["recoverai_training.csv\n(300k rows)"]:::file
        Build --> ValCSV["recoverai_validation.csv\n(60k rows)"]:::file
    end

    subgraph Phase3 [Phase 3: Model Training]
        TrainCSV --> Train["train_catboost.py\nCatBoost Classifier"]:::process
        ValCSV --> Train
        Train --> Model["recoverai_catboost.cbm\n(Trained Model)"]:::output
        Train --> Metrics["metrics.json & feature_importance.csv"]:::output
    end
```

---

## 📁 Project Structure

```text
Revenue-AI-Tracker/
│
├── 📄 README.md                      ← You are here
├── 🌀 index.html                     ← 3D n8n-style Interactive Flow Graph
├── 🎬 assets/flow_animation.gif      ← Custom Python-animated pipeline GIF
│
├── 📥 Step_01_Project_Overview_and_Setup/
├── 📦 Step_02_Data_Collection_and_Ingestion/
├── 🔧 Step_03_Data_Preprocessing_and_Cleaning/
├── 📊 Step_04_Exploratory_Data_Analysis/
├── ⚙️  Step_05_Feature_Engineering/
├── 🤖 Step_06_AI_Model_Training/
├── 📈 Step_07_Model_Evaluation_and_Tuning/
├── 🔌 Step_08_Revenue_Prediction_API/
├── 🖥️  Step_09_Dashboard_and_Visualization/
└── 🐳 Step_10_Deployment_and_Monitoring/
```

---

## ⚡ Quick Start Guide

### 1. Clone & Setup
```bash
git clone https://github.com/viRAJ357/Revenue-AI-Tracker.git
cd Revenue-AI-Tracker
pip install -r backend/requirements.txt
```

### 2. View the 3D Graph
Double-click **`index.html`** → experience the rotating n8n-style 3D flow graph!

### 3. Run the Full Application
```bash
python run.py
```
👉 Open **http://localhost:8000** in your browser.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/process-payment` | Core inference endpoint. Returns recovery decision. |
| `GET`  | `/api/dashboard-stats` | Aggregated metrics for the dashboard. |
| `GET`  | `/api/recent-events` | Fetches 50 most recent recovery attempts. |
| `POST` | `/api/approve-action` | Operator endpoint to approve/reject human_review cases. |
| `GET`  | `/api/health` | Health check for API and Model status. |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| ML Engine | CatBoost Classifier |
| Data Processing | Pandas, NumPy |
| API Backend | FastAPI + Uvicorn |
| Database | SQLite (audit trail) |
| Dashboard | HTML / CSS / JS |
| Containerization | Docker |
| 3D Graph | 3d-force-graph.js |
| Animation | Python Pillow (custom) |

<div align="center">
  <br/>
  <b>Built with AI, motion, and Python — end to end.</b>
  <br/><i>RecoverAI — Turning failed transactions into recovered revenue.</i>
  <br/><br/>
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>
</div>