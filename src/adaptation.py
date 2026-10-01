"""Estado heurístico de adaptação, não uma medição fisiológica."""
from dataclasses import dataclass


DOMAINS = ("aerobic_base", "threshold", "vo2max", "muscular_endurance",
           "anaerobic", "neuromuscular")
CONTRIBUTIONS = {
    "zone2": {"aerobic_base": .08},
    "sweetspot": {"aerobic_base": .03, "muscular_endurance": .07},
    "threshold": {"threshold": .10, "muscular_endurance": .04},
    "vo2max": {"vo2max": .12, "anaerobic": .03},
    "sprint": {"neuromuscular": .15, "anaerobic": .08},
}


@dataclass(frozen=True)
class AdaptationState:
    aerobic_base: float = 0
    threshold: float = 0
    vo2max: float = 0
    muscular_endurance: float = 0
    anaerobic: float = 0
    neuromuscular: float = 0

    def apply(self, stimulus):
        values = self.__dict__.copy()
        for domain, contribution in CONTRIBUTIONS.get(stimulus, {}).items():
            values[domain] = min(1.0, values[domain] + contribution)
        return AdaptationState(**values)

    def decay(self, days, daily_rate=.01):
        factor = max(0, 1 - days * daily_rate)
        return AdaptationState(**{domain: getattr(self, domain) * factor for domain in DOMAINS})
