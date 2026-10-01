"""Decisão adaptativa explicável, sem reduzir o atleta a TSB ou zona."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TrainingDecision:
    goal: str | None
    phase: str
    primary_adaptation: str
    secondary_adaptation: str | None
    selected_zone: str
    workout_family: str
    progression_step: int
    planned_duration: int
    planned_load: float
    readiness_modifier: str
    rationale: str
    confidence: str


class TrainingDecisionEngine:
    """Conecta objetivo, fase, adaptação, carga e readiness em uma decisão."""
    def decide(self, goal, phase, adaptations, recent_load, readiness,
               family, progression_step, duration, planned_load):
        ranked = sorted(adaptations, key=adaptations.get)
        primary = ranked[0] if ranked else "aerobic_base"
        secondary = ranked[1] if len(ranked) > 1 else None
        unfavorable = bool(readiness and (getattr(readiness, "illness", False) or
                                          any(getattr(readiness, "signals", {}).values())))
        if unfavorable or recent_load > planned_load * 1.15:
            return TrainingDecision(goal, phase, primary, secondary, "zone2", "endurance",
                                    progression_step, min(duration, 900), planned_load * .5,
                                    "recovery", "Readiness ou carga recente limita a dose.", "high")
        zone = {"threshold": "threshold", "vo2max": "vo2max",
                "sweet_spot": "sweetspot"}.get(family, "zone2")
        return TrainingDecision(goal, phase, primary, secondary, zone, family,
                                progression_step, duration, planned_load, "none",
                                f"{goal or 'Plano'} em {phase}: prioriza {primary} agora.",
                                "medium")
