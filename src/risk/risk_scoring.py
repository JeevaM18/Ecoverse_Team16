import firebase_admin
from firebase_admin import credentials, firestore
from dataclasses import dataclass
from typing import List
from datetime import datetime
import os

# ==============================
# FIREBASE INITIALIZATION
# ==============================

# Path to Firebase service account key
FIREBASE_KEY_PATH = "activitymotiondetection-firebase-adminsdk-fbsvc-3560a9a703.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==============================
# DATA STRUCTURES
# ==============================

@dataclass
class ActivityEvent:
    timestamp: datetime
    activity: str            # Walk, Static, Transitions, Exercise, Stairs
    fall_prob: float         # 0.0 – 1.0
    is_fall: bool             # True / False


class ActivityHistory:
    def __init__(self):
        self.events: List[ActivityEvent] = []

    def add_event(self, event: ActivityEvent):
        self.events.append(event)

    def last_n_events(self, n=100):
        return self.events[-n:]


# ==============================
# RISK SCORING ENGINE
# ==============================

class RiskScorer:

    def compute_fall_risk(self, events: List[ActivityEvent]) -> float:
        if not events:
            return 0.0

        total = len(events)

        fall_count = sum(e.is_fall for e in events)
        near_fall_count = sum(0.45 <= e.fall_prob < 0.7 for e in events)
        transition_instability = sum(e.activity == "Transitions" for e in events)
        prolonged_inactivity = sum(e.activity == "Static" for e in events) > total * 0.6

        fall_count /= total
        near_fall_count /= total
        transition_instability /= total
        prolonged_inactivity = int(prolonged_inactivity)

        risk = (
            0.4 * fall_count +
            0.3 * near_fall_count +
            0.2 * transition_instability +
            0.1 * prolonged_inactivity
        )

        return round(min(risk * 100, 100), 2)

    def compute_safety_risk(self, events: List[ActivityEvent]) -> float:
        if not events:
            return 0.0

        total = len(events)
        unsafe_exertion = sum(e.activity == "Exercise" for e in events)
        transition_risk = sum(e.activity == "Transitions" for e in events)

        risk = (unsafe_exertion + transition_risk) / total
        return round(min(risk * 100, 100), 2)

    def compute_rehab_progress(self, events: List[ActivityEvent]) -> float:
        if not events:
            return 0.0

        total = len(events)

        walk_ratio = sum(e.activity == "Walk" for e in events) / total
        transition_ratio = sum(e.activity == "Transitions" for e in events) / total
        fall_ratio = sum(e.is_fall for e in events) / total

        progress = (
            0.5 * walk_ratio +
            0.3 * (1 - transition_ratio) +
            0.2 * (1 - fall_ratio)
        )

        return round(progress * 100, 2)


# ==============================
# FIREBASE PUSH FUNCTION
# ==============================

def push_scores_to_firebase(user_id: str,
                            fall_risk: float,
                            safety_risk: float,
                            rehab_progress: float):

    doc = {
        "user_id": user_id,
        "fall_risk_score": fall_risk,
        "safety_risk_score": safety_risk,
        "rehab_progress_score": rehab_progress,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Collection auto-creates if not present
    db.collection("risk_scores").add(doc)

    print("✅ Risk scores pushed to Firebase")


# ==============================
# DEMO / TEST RUN
# ==============================

if __name__ == "__main__":

    history = ActivityHistory()
    scorer = RiskScorer()

    # 🔁 Simulating your fall detection output
    simulated_events = [
        ("Walk", 0.51, True),
        ("Walk", 0.52, True),
        ("Static", 0.50, False),
        ("Transitions", 0.61, False),
        ("Walk", 0.48, False),
        ("Exercise", 0.40, False),
        ("Transitions", 0.58, False),
        ("Static", 0.45, False)
    ]

    for activity, prob, fall in simulated_events:
        history.add_event(ActivityEvent(
            timestamp=datetime.utcnow(),
            activity=activity,
            fall_prob=prob,
            is_fall=fall
        ))

    recent_events = history.last_n_events()

    fall_risk = scorer.compute_fall_risk(recent_events)
    safety_risk = scorer.compute_safety_risk(recent_events)
    rehab_progress = scorer.compute_rehab_progress(recent_events)

    print("Fall Risk Score:", fall_risk)
    print("Safety Risk Score:", safety_risk)
    print("Rehab Progress Score:", rehab_progress)

    # 🔥 Push to Firebase
    push_scores_to_firebase(
        user_id="Elderly_001",
        fall_risk=fall_risk,
        safety_risk=safety_risk,
        rehab_progress=rehab_progress
    )
