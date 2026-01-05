from dataclasses import dataclass
from datetime import datetime
from typing import List

# =========================
# DATA STRUCTURES
# =========================

@dataclass
class RiskSnapshot:
    timestamp: datetime
    fall_risk_score: float   # 0–100


@dataclass
class DriftResult:
    drift_level: str         # Low / Medium / High
    alerts: List[str]        # Narrative drift alerts


# =========================
# CAREGIVER ALERT ENGINE
# =========================

class CaregiverAlertGenerator:

    def __init__(self):
        pass

    # -------------------------
    # Main alert generator
    # -------------------------
    def generate_alert(self,
                       risk_history: List[RiskSnapshot],
                       drift_result: DriftResult) -> dict:

        messages = []
        severity = "Low"

        # -------------------------
        # Risk trend analysis
        # -------------------------
        risk_trend = self._analyze_risk_trend(risk_history)

        if risk_trend == "Increasing":
            messages.append("Fall risk has been increasing steadily over recent days.")
            severity = "Medium"

        if risk_trend == "High":
            messages.append("High fall risk detected. Immediate attention is recommended.")
            severity = "High"

        # -------------------------
        # Drift-based alerts
        # -------------------------
        if drift_result.drift_level == "Medium":
            messages.append("Mobility patterns show noticeable decline compared to baseline.")
            severity = max(severity, "Medium", key=self._severity_rank)

        if drift_result.drift_level == "High":
            messages.append("Significant mobility decline detected over multiple weeks.")
            severity = "High"

        for alert in drift_result.alerts:
            if alert != "No significant mobility drift detected.":
                messages.append(alert)

        # -------------------------
        # Final recommendation
        # -------------------------
        if severity == "High":
            messages.append("Recommend immediate caregiver check-in or medical consultation.")
        elif severity == "Medium":
            messages.append("Recommend caregiver monitoring and follow-up.")
        else:
            messages.append("Mobility stable. No immediate intervention required.")

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity,
            "messages": messages
        }

    # =========================
    # INTERNAL HELPERS
    # =========================

    def _analyze_risk_trend(self, history: List[RiskSnapshot]) -> str:
        if len(history) < 3:
            return "Stable"

        recent = history[-3:]
        scores = [r.fall_risk_score for r in recent]

        if scores[-1] > 70:
            return "High"

        if scores[0] < scores[1] < scores[2]:
            return "Increasing"

        return "Stable"

    def _severity_rank(self, level):
        ranking = {"Low": 0, "Medium": 1, "High": 2}
        return ranking[level]


# =========================
# DEMO / TEST RUN
# =========================

if __name__ == "__main__":

    alert_engine = CaregiverAlertGenerator()

    # -------------------------
    # Simulated risk history
    # -------------------------
    risk_history = [
        RiskSnapshot(datetime.utcnow(), 42.0),
        RiskSnapshot(datetime.utcnow(), 55.0),
        RiskSnapshot(datetime.utcnow(), 68.0),
    ]

    # -------------------------
    # Simulated drift result
    # -------------------------
    drift_result = DriftResult(
        drift_level="High",
        alerts=[
            "Walking activity has declined compared to baseline.",
            "Prolonged inactivity compared to baseline."
        ]
    )

    # -------------------------
    # Generate caregiver alert
    # -------------------------
    caregiver_alert = alert_engine.generate_alert(
        risk_history=risk_history,
        drift_result=drift_result
    )

    print("Caregiver Alert:")
    print("Severity:", caregiver_alert["severity"])
    print("Messages:")
    for msg in caregiver_alert["messages"]:
        print("-", msg)
