from datetime import datetime, timezone
from collections import defaultdict

from src.utils.firebase_client import push_to_firebase

# ===============================
# ROLE CONSTANTS
# ===============================

ELDERLY = "elderly"
EMPLOYEE = "employee"
REHAB = "rehab"


# ===============================
# CONTEXT ENGINE
# ===============================

class ContextEngine:
    """
    Routes activity events to different interpretations
    based on user role and environment context.
    """

    def __init__(self):
        self.workplace_violations = defaultdict(int)

    # --------------------------------------------------
    # MAIN ROUTER
    # --------------------------------------------------
    def route_event(self, user_profile, activity_event, zone_event=None):
        role = user_profile["role"]

        if role == ELDERLY:
            result = self._elderly_logic(activity_event)
            push_to_firebase("elderly_context_events", result)
            return result

        if role == EMPLOYEE:
            result = self._workplace_logic(activity_event, zone_event)
            push_to_firebase("workplace_context_events", result)
            return result

        if role == REHAB:
            result = self._rehab_logic(activity_event)
            push_to_firebase("rehab_context_events", result)
            return result

        unknown = {
            "domain": "unknown",
            "timestamp": self._utc_time(),
            "message": "Unknown user role"
        }
        push_to_firebase("unknown_events", unknown)
        return unknown

    # ==================================================
    # ELDERLY CARE LOGIC
    # ==================================================
    def _elderly_logic(self, activity_event):

        insights = []
        risk_contributors = []

        activity = activity_event["activity"]
        fall_prob = activity_event.get("fall_prob", 0.0)

        if activity == "Walk":
            insights.append("Walking activity observed")

        if activity == "Transitions":
            insights.append("Instability detected during posture change")
            risk_contributors.append("transition_instability")

        if activity == "Static":
            insights.append("Prolonged inactivity detected")
            risk_contributors.append("inactivity")

        if activity == "Exercise":
            insights.append("Fatigue risk detected")

        if activity == "Stairs":
            insights.append("Stair usage increases fall risk")
            risk_contributors.append("stairs_risk")

        if fall_prob > 0.6:
            insights.append("High fall risk detected")
            risk_contributors.append("fall_risk")

        return {
            "domain": "elderly",
            "timestamp": self._utc_time(),
            "user_id": activity_event["user_id"],
            "activity": activity,
            "fall_probability": round(fall_prob, 2),
            "insights": insights,
            "risk_contributors": risk_contributors,
            "output": "Caregiver alert / preventive recommendation"
        }

    # ==================================================
    # WORKPLACE SAFETY LOGIC
    # ==================================================
    def _workplace_logic(self, activity_event, zone_event):

        violations = []

        activity = activity_event["activity"]
        user_id = activity_event["user_id"]

        if zone_event:
            zone = zone_event["zone"]

            if zone == "Restricted_Zone" and activity == "Walk":
                violations.append("Restricted zone entry")
                self.workplace_violations[user_id] += 1

            if zone == "Hazard_Zone" and activity == "Stairs":
                violations.append("Hazard zone stair activity")
                self.workplace_violations[user_id] += 1
        else:
            zone = "Unknown"

        if activity == "Exercise":
            violations.append("Overexertion risk")
            self.workplace_violations[user_id] += 1

        if activity == "Static":
            violations.append("Possible collapse risk")
            self.workplace_violations[user_id] += 1

        if activity == "Transitions":
            violations.append("Unsafe posture detected")
            self.workplace_violations[user_id] += 1

        violation_count = self.workplace_violations[user_id]
        escalation = self._escalation_level(violation_count)
        safety_score = max(100 - (violation_count * 15), 0)

        return {
            "domain": "workplace",
            "timestamp": self._utc_time(),
            "user_id": user_id,
            "activity": activity,
            "zone": zone,
            "violations": violations,
            "violation_count": violation_count,
            "escalation_level": escalation,
            "safety_score": safety_score,
            "output": "Warning / Supervisor / Admin escalation"
        }

    # ==================================================
    # REHAB LOGIC (Placeholder)
    # ==================================================
    def _rehab_logic(self, activity_event):
        return {
            "domain": "rehab",
            "timestamp": self._utc_time(),
            "user_id": activity_event["user_id"],
            "activity": activity_event["activity"],
            "status": "Tracked for rehabilitation analysis"
        }

    # ==================================================
    # ESCALATION RULES
    # ==================================================
    def _escalation_level(self, count):
        if count >= 5:
            return "Admin Escalation"
        elif count >= 3:
            return "Supervisor Alert"
        elif count >= 1:
            return "Warning"
        else:
            return "No Action"

    # ==================================================
    # TIME UTILITY
    # ==================================================
    def _utc_time(self):
        return datetime.now(timezone.utc).isoformat()


# ==================================================
# DEMO / TEST RUN
# ==================================================
if __name__ == "__main__":

    engine = ContextEngine()

    # Elderly example
    elderly_user = {"user_id": "ELD_01", "role": ELDERLY}
    elderly_event = {
        "user_id": "ELD_01",
        "activity": "Transitions",
        "fall_prob": 0.72
    }

    print("Elderly Output:")
    print(engine.route_event(elderly_user, elderly_event))

    # Workplace example
    employee_user = {"user_id": "EMP_101", "role": EMPLOYEE}
    activity_event = {
        "user_id": "EMP_101",
        "activity": "Walk"
    }
    zone_event = {
        "zone": "Restricted_Zone"
    }

    print("\nWorkplace Output:")
    print(engine.route_event(employee_user, activity_event, zone_event))
