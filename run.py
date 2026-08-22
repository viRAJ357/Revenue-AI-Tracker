"""
RecoverAI — Start Everything
Run this file to launch the complete RecoverAI system.
"""
import sys
import os
import subprocess
import time
import webbrowser

print("=" * 65)
print("  RecoverAI — System Launcher")
print("=" * 65)

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")

# Step 1: Install dependencies
print("\n[1/3] Installing dependencies...")
subprocess.run(
    [sys.executable, "-m", "pip", "install",
     "fastapi", "uvicorn[standard]", "catboost",
     "pandas", "numpy", "pydantic", "scikit-learn", "-q"],
    check=True
)
print("  Dependencies ready!")

# Step 2: Init database
print("\n[2/3] Initializing database...")
sys.path.insert(0, BACKEND)
try:
    from database import init_db
    init_db()
    print("  Database ready!")
except Exception as e:
    print(f"  DB init: {e}")

# Step 3: Launch FastAPI server
print("\n[3/3] Starting RecoverAI backend on http://localhost:8000")
print("  API Docs -> http://localhost:8000/docs")
print("  Dashboard -> Open frontend/index.html in browser")
print("\n  Press Ctrl+C to stop.\n")
print("=" * 65)

# Open dashboard in browser after 2 seconds
def open_browser():
    time.sleep(2)
    dashboard = os.path.join(ROOT, "frontend", "index.html")
    webbrowser.open(f"file:///{dashboard}")

import threading
t = threading.Thread(target=open_browser, daemon=True)
t.start()

# Start uvicorn
os.chdir(ROOT)
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "backend.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
])
