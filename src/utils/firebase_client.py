import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

# =========================
# INITIALIZE FIREBASE ONCE
# =========================
service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")

if not service_account_path:
    raise ValueError("FIREBASE_SERVICE_ACCOUNT not set in environment")

if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =========================
# PUSH HELPER
# =========================
def push_to_firebase(collection: str, data: dict):
    data["timestamp"] = firestore.SERVER_TIMESTAMP
    db.collection(collection).add(data)
