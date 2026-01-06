# src/rehab/rehablitation_alcoholic_index.py

import pickle
import pandas as pd
import os
from datetime import datetime, timezone

from src.utils.firebase_client import push_to_firebase

# ==============================
# CONFIG
# ==============================

USER_ID = "ALC_001"

MODEL_DIR = "models"

SLEEP_MODEL_PATH = os.path.join(MODEL_DIR, "sleep_quality_model.pkl")
STRESS_MODEL_PATH = os.path.join(MODEL_DIR, "stress_regulation_model.pkl")

# ==============================
# Utility: Test pickle loading
# ==============================

def test_pickle(file):
    with open(file, "rb") as f:
        _ = pickle.load(f)
    print(f"✅ {os.path.basename(file)} loaded successfully")

test_pickle(SLEEP_MODEL_PATH)
test_pickle(STRESS_MODEL_PATH)

# ==============================
# Load model bundles
# ==============================

with open(SLEEP_MODEL_PATH, "rb") as f:
    sleep_bundle = pickle.load(f)

with open(STRESS_MODEL_PATH, "rb") as f:
    stress_bundle = pickle.load(f)

sleep_model = sleep_bundle["model"]
stress_model = stress_bundle["model"]

sleep_features = sleep_bundle["features"]
stress_features = stress_bundle["features"]

print("\nSleep model expects features:")
print(sleep_features)

print("\nStress model expects features:")
print(stress_features)

# ==============================
# Dummy input (replace later)
# ==============================

sleep_input = pd.DataFrame(
    [[0] * len(sleep_features)],
    columns=sleep_features
)

stress_input = pd.DataFrame(
    [[0] * len(stress_features)],
    columns=stress_features
)

# ==============================
# Sleep Model Inference
# ==============================

sleep_prob = sleep_model.predict_proba(sleep_input)
sleep_score = round(float(sleep_prob[0, 1] * 100), 2)

# ==============================
# Stress Model Inference
# ==============================

stress_probs = stress_model.predict_proba(stress_input)

stress_score = round(
    (stress_probs[0, 0] + 0.5 * stress_probs[0, 1]) * 100,
    2
)

# ==============================
# RSI Computation
# ==============================

rsi_score = round(
    0.5 * sleep_score + 0.5 * stress_score,
    2
)

# ==============================
# RSI Status Mapping
# ==============================

def assign_rsi_status(score):
    if score < 30:
        return "High Risk"
    elif score < 60:
        return "Early Recovery"
    else:
        return "Stable Recovery"

rsi_status = assign_rsi_status(rsi_score)

# ==============================
# FIREBASE PAYLOAD
# ==============================

firebase_payload = {
    "user_id": USER_ID,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sleep_quality_score": sleep_score,
    "stress_regulation_score": stress_score,
    "rehabilitation_status_index": rsi_score,
    "rsi_status": rsi_status
}

# ==============================
# PUSH TO FIREBASE
# ==============================

push_to_firebase(
    "alcohol_rehab_predictions",
    firebase_payload
)

# ==============================
# FINAL OUTPUT
# ==============================

print("\nFinal RSI Output")
print("----------------")
print("Sleep Quality Score:", sleep_score)
print("Stress Regulation Score:", stress_score)
print("RSI Score:", rsi_score)
print("RSI Status:", rsi_status)
print("✅ Result pushed to Firebase")
