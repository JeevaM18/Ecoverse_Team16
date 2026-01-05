from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

# =========================
# DATA STRUCTURE
# =========================

@dataclass
class ActivityEvent:
    timestamp: datetime
    activity: str  # Walk, Static, Transitions, Exercise, Stairs


# =========================
# BASELINE vs DRIFT ENGINE
# =========================

class BaselineDriftDetector:

    def __init__(self, baseline_days: int = 7):
        self.baseline_days = baseline_days
        self.daily_events = defaultdict(list)

    # -------------------------
    # Add activity event
    # -------------------------
    def add_event(self, event: ActivityEvent):
        day = event.timestamp.date()
        self.daily_events[day].append(event)

    # -------------------------
    # Compute baseline metrics
    # -------------------------
    def compute_baseline(self, start_day):
        baseline_events = []

        for i in range(self.baseline_days):
            day = start_day + timedelta(days=i)
            baseline_events.extend(self.daily_events.get(day, []))

        return self._extract_metrics(baseline_events)

    # -------------------------
    # Compute current week metrics
    # -------------------------
    def compute_current_week(self, end_day):
        current_events = []

        for i in range(7):
            day = end_day - timedelta(days=i)
            current_events.extend(self.daily_events.get(day, []))

        return self._extract_metrics(current_events)

    # -------------------------
    # Drift detection
    # -------------------------
    def detect_drift(self, baseline, current):
        drift_score = 0
        alerts = []

        # Walking decline
        if current["walk"] < baseline["walk"] * 0.8:
            drift_score += 1
            alerts.append("Walking activity has declined compared to baseline.")

        # Transition increase
        if current["transitions"] > baseline["transitions"] * 1.2:
            drift_score += 1
            alerts.append("Increase in unstable transitions detected.")

        # Inactivity increase
        if current["static"] > baseline["static"] * 1.25:
            drift_score += 1
            alerts.append("Prolonged inactivity compared to baseline.")

        drift_level = self._map_drift_level(drift_score)

        if not alerts:
            alerts.append("No significant mobility drift detected.")

        return {
            "drift_score": drift_score,
            "drift_level": drift_level,
            "alerts": alerts
        }

    # =========================
    # INTERNAL HELPERS
    # =========================

    def _extract_metrics(self, events: List[ActivityEvent]):
        if not events:
            return {"walk": 0, "transitions": 0, "static": 0}

        return {
            "walk": sum(e.activity == "Walk" for e in events),
            "transitions": sum(e.activity == "Transitions" for e in events),
            "static": sum(e.activity == "Static" for e in events)
        }

    def _map_drift_level(self, score):
        if score == 0:
            return "Low"
        elif score == 1:
            return "Medium"
        else:
            return "High"


# =========================
# DEMO / TEST RUN
# =========================

if __name__ == "__main__":

    detector = BaselineDriftDetector(baseline_days=7)
    today = datetime.now().date()

    # -------------------------
    # Simulated baseline (healthy)
    # -------------------------
    for d in range(14, 7, -1):
        day = today - timedelta(days=d)
        for _ in range(40):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Walk"
            ))
        for _ in range(5):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Transitions"
            ))
        for _ in range(10):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Static"
            ))

    # -------------------------
    # Simulated current week (decline)
    # -------------------------
    for d in range(7):
        day = today - timedelta(days=d)
        for _ in range(20):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Walk"
            ))
        for _ in range(15):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Transitions"
            ))
        for _ in range(25):
            detector.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time()),
                activity="Static"
            ))

    # -------------------------
    # Run drift detection
    # -------------------------
    baseline_metrics = detector.compute_baseline(today - timedelta(days=14))
    current_metrics = detector.compute_current_week(today)

    result = detector.detect_drift(baseline_metrics, current_metrics)

    print("Baseline Metrics:", baseline_metrics)
    print("Current Week Metrics:", current_metrics)
    print("Drift Level:", result["drift_level"])
    print("Narrative Alerts:")
    for alert in result["alerts"]:
        print("-", alert)
