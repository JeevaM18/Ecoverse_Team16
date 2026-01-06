from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List
from dataclasses import dataclass

from src.utils.firebase_client import push_to_firebase

# =========================
# DATA STRUCTURE
# =========================

@dataclass
class ActivityEvent:
    timestamp: datetime
    activity: str           # Walk, Static, Transitions, Exercise, Stairs
    fall_prob: float
    is_fall: bool


# =========================
# MOTION BIOGRAPHY ENGINE
# =========================

class MotionBiography:

    def __init__(self):
        self.daily_data = defaultdict(list)

    # -------------------------
    # Add events
    # -------------------------
    def add_event(self, event: ActivityEvent):
        self.daily_data[event.timestamp.date()].append(event)

    # -------------------------
    # Daily summary
    # -------------------------
    def generate_daily_summary(self, user_id: str, day):
        events = self.daily_data.get(day, [])
        if not events:
            return None

        summary = {
            "user_id": user_id,
            "date": str(day),
            "walking_duration": sum(e.activity == "Walk" for e in events),
            "transition_count": sum(e.activity == "Transitions" for e in events),
            "near_falls": sum(0.45 <= e.fall_prob < 0.7 for e in events),
            "inactivity_time": sum(e.activity == "Static" for e in events),
            "fall_risk_score": self._compute_fall_risk(events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 🔥 Store daily biography
        push_to_firebase("elderly_motion_biography_daily", summary)

        return summary

    # -------------------------
    # Weekly comparison
    # -------------------------
    def generate_weekly_trend(self, user_id: str, end_day):
        this_week = []
        last_week = []

        for i in range(7):
            this_week.extend(self.daily_data.get(end_day - timedelta(days=i), []))
            last_week.extend(self.daily_data.get(end_day - timedelta(days=i + 7), []))

        trend = self._compare_weeks(this_week, last_week)
        narratives = self.generate_narrative(trend)

        payload = {
            "user_id": user_id,
            "week_ending": str(end_day),
            "trend_metrics": trend,
            "narratives": narratives,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 🔥 Store weekly biography
        push_to_firebase("elderly_motion_biography_weekly", payload)

        return payload

    # -------------------------
    # Narrative generation
    # -------------------------
    def generate_narrative(self, weekly_trend):
        narratives = []

        if weekly_trend["walk_change"] <= -20:
            narratives.append("Walking duration reduced significantly this week.")

        if weekly_trend["near_fall_change"] >= 20:
            narratives.append("Near-fall frequency has increased over recent days.")

        if weekly_trend["inactivity_change"] >= 25:
            narratives.append("Prolonged inactivity observed. Mobility may be declining.")

        if not narratives:
            narratives.append("Mobility stable. No immediate intervention required.")

        return narratives

    # =========================
    # INTERNAL METHODS
    # =========================

    def _compute_fall_risk(self, events):
        total = len(events)
        if total == 0:
            return 0.0

        fall_count = sum(e.is_fall for e in events)
        near_falls = sum(0.45 <= e.fall_prob < 0.7 for e in events)
        transitions = sum(e.activity == "Transitions" for e in events)
        inactivity = sum(e.activity == "Static" for e in events)

        risk = (
            0.4 * (fall_count / total) +
            0.3 * (near_falls / total) +
            0.2 * (transitions / total) +
            0.1 * (inactivity / total)
        )

        return round(min(risk * 100, 100), 2)

    def _compare_weeks(self, this_week, last_week):

        def extract_metrics(events):
            if not events:
                return {"walk": 0, "near_fall": 0, "inactivity": 0}

            return {
                "walk": sum(e.activity == "Walk" for e in events),
                "near_fall": sum(0.45 <= e.fall_prob < 0.7 for e in events),
                "inactivity": sum(e.activity == "Static" for e in events)
            }

        curr = extract_metrics(this_week)
        prev = extract_metrics(last_week)

        def pct_change(curr, prev):
            if prev == 0:
                return 0
            return round(((curr - prev) / prev) * 100, 2)

        return {
            "walk_change": pct_change(curr["walk"], prev["walk"]),
            "near_fall_change": pct_change(curr["near_fall"], prev["near_fall"]),
            "inactivity_change": pct_change(curr["inactivity"], prev["inactivity"])
        }


# =========================
# DEMO / TEST RUN
# =========================

if __name__ == "__main__":

    mb = MotionBiography()
    today = datetime.now(timezone.utc).date()
    user_id = "ELDER_001"

    # Simulated activity stream (14 days)
    for d in range(14):
        day = today - timedelta(days=d)
        for _ in range(50):
            mb.add_event(ActivityEvent(
                timestamp=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc),
                activity="Walk" if d < 7 else "Static",
                fall_prob=0.55 if d < 7 else 0.30,
                is_fall=False
            ))

        # Generate daily summary
        mb.generate_daily_summary(user_id, day)

    # Generate weekly trend
    weekly_result = mb.generate_weekly_trend(user_id, today)

    print("Weekly Trend Metrics:", weekly_result["trend_metrics"])
    print("Narrative Insights:")
    for n in weekly_result["narratives"]:
        print("-", n)
