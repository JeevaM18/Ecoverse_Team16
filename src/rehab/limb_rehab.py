# src/rehab/limb_rehab.py

import pickle
import pandas as pd
import os
from datetime import datetime, timezone

from src.utils.firebase_client import push_to_firebase

# ==============================
# CONFIG
# ==============================

USER_ID = "REB_001"   # Change dynamically later if needed

MODEL_DIR = "models"
MODEL_FILE = "rehab_rsi_model.pkl"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILE)

# ==============================
# LOAD MODEL
# ==============================

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print("✅ Rehab RSI model loaded successfully")
except Exception as e:
    print("❌ Failed to load Rehab RSI model")
    raise e

# ==============================
# REQUIRED FEATURE ORDER
# (MUST match training)
# ==============================

FEATURES = [
    "acc_variance",
    "acc_jerk",
    "step_regularity",
    "gyro_variance",
    "acc_energy"
]

# ==============================
# SAMPLE PATIENT INPUT
# (replace with real sensor features)
# ==============================

patient_data = {
    "acc_variance": 0.013,
    "acc_jerk": 0.045,
    "step_regularity": 7.2,
    "gyro_variance": 0.12,
    "acc_energy": 10.5
}

X_patient = pd.DataFrame([patient_data], columns=FEATURES)

# ==============================
# PREDICT RSI
# ==============================

predicted_rsi = float(model.predict(X_patient)[0])
predicted_rsi = round(predicted_rsi, 2)

# ==============================
# INTERPRET RSI (CLINICAL)
# ==============================

if predicted_rsi >= 70:
    rehab_status = "Good Recovery"
elif predicted_rsi >= 50:
    rehab_status = "Moderate Recovery"
else:
    rehab_status = "Needs Improvement"

# ==============================
# PREPARE FIREBASE PAYLOAD
# ==============================

rehab_result = {
    "user_id": USER_ID,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "features": patient_data,
    "predicted_rsi": predicted_rsi,
    "rehab_status": rehab_status
}

# ==============================
# PUSH TO FIREBASE
# ==============================

push_to_firebase(
    "rehab_predictions",   # collection name (positional)
    rehab_result
)

# ==============================
# CONSOLE OUTPUT
# ==============================

print("\nPredicted Rehabilitation Status Index (RSI):", predicted_rsi)
print("Rehab Status:", rehab_status)
print("✅ Rehab result pushed to Firebase")
