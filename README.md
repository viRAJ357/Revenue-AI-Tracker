# AI Revenue Recovery – Hackathon Submission

## Project Overview

**AI Revenue Recovery** is a data‑driven solution that predicts whether a financial transaction will be recovered within 72 hours. Using a CatBoost classifier trained on a carefully engineered feature set, the model achieves strong performance (AUC‑ROC ≈ 0.82, Accuracy ≈ 74 %). The repository contains the full end‑to‑end pipeline:

- **Data preparation** (`build_recoverai_dataset.py`, `download_datasets.py`)
- **Exploratory data analysis** (`eda_analysis.py`, `eda_fast.py`)
- **Model training** (`train_catboost.py`)
- **Model serving / inference** (`run.py`)
- **Frontend UI** (React/Vite under `frontend/`)
- **Backend API** (`backend/`)

The solution is packaged for easy local execution and also ready for cloud deployment.

## 3‑D Workflow with **GSOX Motion**

The project follows a **3‑D (Data‑Model‑Deploy) workflow** orchestrated by the **GSOX motion workflow**:

1. **Data** – Raw CSV files are stored under `datasets/`. `build_recoverai_dataset.py` cleans, fills missing values, and splits the data into `recoverai_training.csv` and `recoverai_validation.csv`.
2. **Model** – `train_catboost.py` consumes the processed data, performs feature selection, trains a CatBoost classifier, evaluates performance, saves the model (`model/recoverai_catboost.cbm`), feature importance, and a JSON metrics summary.
3. **Deploy** – `run.py` loads the saved model and exposes a simple HTTP endpoint for inference. The frontend consumes this API to display predictions in real‑time.

The **GSOX motion** automates the hand‑off between each stage, ensuring reproducibility for the hackathon judges:
- Each stage logs key artefacts (model, metrics, feature importance) to the `model/` folder.
- The GitHub Actions workflow (see below) runs the full pipeline on every push, guaranteeing that the repository is always in a runnable state.

## Installation & Quick Start

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/viRAJ357/AI-Revenue-recovery-421.git
cd AI-Revenue-recovery-421

# Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt  # (if a requirements.txt is added) or manually:
pip install catboost pandas scikit-learn

# Train the model (will recreate artefacts in model/)
python train_catboost.py

# Run the inference server
python run.py
```

The server starts on `http://localhost:8000` (default) and the frontend can be launched with `npm install && npm run dev` inside the `frontend/` folder.

## Hackathon Submission Details

- **Team Name:** *[Your Team Name]*
- **Project Title:** AI Revenue Recovery – Predicting Transaction Recovery
- **Repository:** https://github.com/viRAJ357/AI-Revenue-recovery-421
- **Key Deliverables:**
  - Trained model (`model/recoverai_catboost.cbm`)
  - Evaluation metrics (`model/metrics.json`)
  - Full reproducible pipeline (data → model → deployment)
  - Detailed README (this file) and CI workflow
- **Demo Video:** *(Provide a link to a short demo video if required)*

## Continuous Integration (GitHub Actions)

A CI workflow is defined in `.github/workflows/ci.yml`. On every push it:
1. Checks out the code.
2. Sets up Python 3.11.
3. Installs dependencies.
4. Runs `train_catboost.py`.
5. Uploads the generated artefacts as build artefacts for the judges to inspect.

This ensures the repository is always in a buildable, runnable state for the hackathon evaluation.

---
*All code is released under the MIT licence (see `LICENSE`).*