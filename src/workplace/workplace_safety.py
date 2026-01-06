from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from collections import defaultdict

from src.utils.firebase_client import push_to_firebase

# =====================================
# DATA STRUCTURES
# =====================================

@dataclass
class ZoneEvent:
    user_id: str
    zone: str                 # Restricted_Zone, Safe_Zone, Hazard_Zone
    timestamp: datetime


@dataclass
class ActivityEvent:
    user_id: str
    activity: str             # Walk, Static, Transitions, Exercise, Stairs
    timestamp: datetime


@dataclass
class Violation:
    user_id: str
    violation_type: str
    severity: str             # Low / Medium / High
    timestamp: datetime


# =====================================
# WORKPLACE SAFETY ENGINE
# =====================================

class WorkplaceSafetyEngine:

    def __init__(self):
        self.violations: List[Violation] = []
        self.user_violation_count = defaultdict(int)

    # ---------------------------------
    # STEP 2: Zone + Activity Fusion
    # ---------------------------------
    def evaluate_event(self,
                       zone_event: ZoneEvent,
                       activity_event: ActivityEvent):

        if zone_event.user_id != activity_event.user_id:
            return

        user = zone_event.user_id

        # Rule 1: Restricted zone entry
        if zone_event.zone == "Restricted_Zone" and activity_event.activity == "Walk":
            self._log_violation(
                user,
                "Unauthorized entry into restricted zone",
                "High",
                zone_event.zone
            )

        # Rule 2: Overexertion
        if activity_event.activity == "Exercise":
            self._log_violation(
                user,
                "Overexertion detected",
                "Medium",
                zone_event.zone
            )

        # Rule 3: Prolonged inactivity
        if activity_event.activity == "Static":
            self._log_violation(
                user,
                "Prolonged inactivity (collapse risk)",
                "Medium",
                zone_event.zone
            )

    # ---------------------------------
    # STEP 3: Violation logging
    # ---------------------------------
    def _log_violation(self, user_id, violation_type, severity, zone):
        self.user_violation_count[user_id] += 1

        violation = Violation(
            user_id=user_id,
            violation_type=violation_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc)
        )

        self.violations.append(violation)

        # 🔥 Push violation to Firebase
        push_to_firebase(
            "workplace_violations",
            {
                "user_id": user_id,
                "violation_type": violation_type,
                "severity": severity,
                "zone": zone,
                "timestamp": violation.timestamp.isoformat()
            }
        )

    # ---------------------------------
    # STEP 3: Escalation Logic
    # ---------------------------------
    def get_escalation_level(self, user_id):
        count = self.user_violation_count[user_id]

        if count >= 5:
            return "Admin Escalation"
        elif count >= 3:
            return "Supervisor Alert"
        elif count >= 1:
            return "Warning"
        else:
            return "No Action"

    # ---------------------------------
    # STEP 4: Safety Score & Metrics
    # ---------------------------------
    def compute_safety_score(self, user_id):
        count = self.user_violation_count[user_id]
        return max(100 - (count * 15), 0)

    def zone_risk_level(self, zone):
        if zone == "Restricted_Zone":
            return "High"
        elif zone == "Hazard_Zone":
            return "Medium"
        else:
            return "Low"

    # ---------------------------------
    # STEP 4: Push dashboard metrics
    # ---------------------------------
    def push_dashboard_metrics(self, user_id, zone):

        payload = {
            "user_id": user_id,
            "violation_count": self.user_violation_count[user_id],
            "escalation_level": self.get_escalation_level(user_id),
            "safety_score": self.compute_safety_score(user_id),
            "zone_risk_level": self.zone_risk_level(zone),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        push_to_firebase("workplace_safety_dashboard", payload)

        return payload


# =====================================
# DEMO / TEST RUN
# =====================================

if __name__ == "__main__":

    engine = WorkplaceSafetyEngine()

    user = "EMP_101"

    zone_events = [
        ZoneEvent(user, "Restricted_Zone", datetime.now(timezone.utc)),
        ZoneEvent(user, "Safe_Zone", datetime.now(timezone.utc)),
    ]

    activity_events = [
        ActivityEvent(user, "Walk", datetime.now(timezone.utc)),
        ActivityEvent(user, "Exercise", datetime.now(timezone.utc)),
        ActivityEvent(user, "Static", datetime.now(timezone.utc)),
    ]

    for z, a in zip(zone_events, activity_events):
        engine.evaluate_event(z, a)

    dashboard = engine.push_dashboard_metrics(user, "Restricted_Zone")

    print("Violations Logged:")
    for v in engine.violations:
        print(f"- {v.violation_type} | Severity: {v.severity}")

    print("\nDashboard Metrics:")
    for k, v in dashboard.items():
        print(f"{k}: {v}")
