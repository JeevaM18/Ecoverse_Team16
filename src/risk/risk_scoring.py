import firebase_admin
from firebase_admin import credentials, firestore
from dataclasses import dataclass
from typing import List
from datetime import datetime
import os

from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ==============================
# FIREBASE INITIALIZATION
# ==============================

FIREBASE_KEY_PATH = "activitymotiondetection-firebase-adminsdk-fbsvc-3560a9a703.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==============================
# TWILIO INITIALIZATION
# ==============================

twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
alert_to = os.getenv("ALERT_PHONE_NUMBER")
fall_risk_threshold = float(os.getenv("FALL_RISK_THRESHOLD", "50.0"))

if not all([twilio_sid, twilio_token, twilio_from, alert_to]):
    print("⚠️  Twilio credentials missing in .env – SMS alerts disabled.")
    twilio_client = None
else:
    twilio_client = Client(twilio_sid, twilio_token)

def send_sms_alert(user_id: str, fall_risk: float):
    if twilio_client is None:
        print("⚠️  SMS alert skipped (Twilio not configured).")
        return

    message_body = (
        f"🚨 HIGH FALL RISK ALERT 🚨\n"
        f"User: {user_id}\n"
        f"Fall Risk Score: {fall_risk:.2f}%\n"
        f"Immediate attention recommended!\n"
        f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    try:
        message = twilio_client.messages.create(
            body=message_body,
            from_=twilio_from,
            to=alert_to
        )
        print(f"✅ SMS alert sent! SID: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send SMS: {e}")

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

    db.collection("risk_scores").add(doc)
    print("✅ Risk scores pushed to Firebase")


# ==============================
# DEMO / TEST RUN
# ==============================

if __name__ == "__main__":

    history = ActivityHistory()
    scorer = RiskScorer()

       # Simulating events to TRIGGER ALERT: Fall Risk > 50
    simulated_events = [
        ("Walk", 0.65, True),          # Fall
        ("Walk", 0.72, True),          # Fall
        ("Transitions", 0.68, True),   # Fall during transition
        ("Static", 0.55, False),       # Near-fall
        ("Transitions", 0.62, False),  # Instability
        ("Walk", 0.59, False),         # Near-fall
        ("Transitions", 0.70, True),   # Fall
        ("Static", 0.48, False),
        ("Exercise", 0.45, False),
        ("Walk", 0.50, False),
        # Extra events to push fall risk over 50
        ("Transitions", 0.75, True),   # Another fall in transition
        ("Exercise", 0.60, True),      # Fall during exercise
        ("Transitions", 0.65, False),  # More instability
        ("Transitions", 0.70, True),   # One more fall
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

    # Push to Firebase
    user_id = "Elderly_001"
    push_scores_to_firebase(
        user_id=user_id,
        fall_risk=fall_risk,
        safety_risk=safety_risk,
        rehab_progress=rehab_progress
    )

    # Check threshold and send SMS alert
    if fall_risk > fall_risk_threshold:
        print(f"🚨 Fall risk ({fall_risk}) exceeds threshold ({fall_risk_threshold}) – sending alert!")
        send_sms_alert(user_id, fall_risk)
    else:
        print(f"✅ Fall risk ({fall_risk}) is below threshold – no alert sent.")