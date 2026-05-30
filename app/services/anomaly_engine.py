from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from app.services.conversion_engine import ConversionEngine, _get_field


class AnomalyEngine:
    """Service class responsible for executing retail anomaly detection algorithms."""

    @classmethod
    def detect_anomalies(
        self, sessions: Sequence[Any], evaluation_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Orchestrates queue spike, conversion drop, and dead zone anomaly checks."""
        if not sessions:
            return []

        # Enforce timezone-aware evaluation time
        if evaluation_time is None:
            entered_times = [
                _get_field(s, "entered_at")
                for s in sessions
                if _get_field(s, "entered_at") is not None
            ]
            evaluation_time = max(entered_times) if entered_times else datetime.now(timezone.utc)
        
        if evaluation_time.tzinfo is None:
            evaluation_time = evaluation_time.replace(tzinfo=timezone.utc)

        anomalies = []
        anomalies.extend(self._detect_queue_spike(sessions, evaluation_time))
        anomalies.extend(self._detect_conversion_drop(sessions, evaluation_time))
        anomalies.extend(self._detect_dead_zones(sessions, evaluation_time))
        return anomalies

    @classmethod
    def _detect_queue_spike(
        cls, sessions: Sequence[Any], evaluation_time: datetime
    ) -> list[dict[str, Any]]:
        """Flags high-severity queue spikes when checkout depth exceeds double the baseline."""
        current_cutoff = evaluation_time - timedelta(minutes=15)
        historical_cutoff = evaluation_time - timedelta(hours=4)

        current_sessions = []
        historical_sessions = []

        for s in sessions:
            entered = _get_field(s, "entered_at")
            if entered is None:
                continue
            if entered.tzinfo is None:
                entered = entered.replace(tzinfo=timezone.utc)

            if current_cutoff <= entered <= evaluation_time:
                current_sessions.append(s)
            elif historical_cutoff <= entered < current_cutoff:
                historical_sessions.append(s)

        current_queue_depth = sum(
            1 for s in current_sessions if _get_field(s, "has_joined_billing_queue", False)
        )
        historical_queue_depth = sum(
            1 for s in historical_sessions if _get_field(s, "has_joined_billing_queue", False)
        )

        # Baseline window is 225 minutes, meaning 15 blocks of 15 minutes.
        baseline = historical_queue_depth / 15.0

        # No manufactured baseline. Do not flag if historical queue baseline is zero.
        if baseline <= 0.0:
            return []

        # Validate robust queue spike thresholds
        if (
            current_queue_depth >= 3
            and current_queue_depth > 2 * baseline
            and current_queue_depth - baseline >= 2
        ):
            return [
                {
                    "type": "QUEUE_SPIKE",
                    "severity": "HIGH",
                    "title": "Queue Spike Detected",
                    "description": f"Current queue depth ({current_queue_depth}) exceeds historical baseline ({baseline:.2f}).",
                    "affected_zone": None,
                    "suggested_action": "Open additional billing counters",
                    "metric_value": float(current_queue_depth),
                    "baseline_value": float(round(baseline, 2)),
                    "generated_at": evaluation_time,
                }
            ]

        return []

    @classmethod
    def _detect_conversion_drop(
        cls, sessions: Sequence[Any], evaluation_time: datetime
    ) -> list[dict[str, Any]]:
        """Flags high-severity purchase rate drop-offs relative to the previous time window."""
        current_cutoff = evaluation_time - timedelta(minutes=30)
        previous_cutoff = evaluation_time - timedelta(minutes=60)

        current_sessions = []
        previous_sessions = []

        for s in sessions:
            entered = _get_field(s, "entered_at")
            if entered is None:
                continue
            if entered.tzinfo is None:
                entered = entered.replace(tzinfo=timezone.utc)

            if current_cutoff <= entered <= evaluation_time:
                current_sessions.append(s)
            elif previous_cutoff <= entered < current_cutoff:
                previous_sessions.append(s)

        # Avoid alerting on tiny, non-representative sample sizes
        if len(current_sessions) < 2 or len(previous_sessions) < 2:
            return []

        current_purchases = sum(
            1 for s in current_sessions if _get_field(s, "has_converted", False)
        )
        previous_purchases = sum(
            1 for s in previous_sessions if _get_field(s, "has_converted", False)
        )

        current_rate = (current_purchases / len(current_sessions)) * 100.0
        previous_rate = (previous_purchases / len(previous_sessions)) * 100.0

        if previous_rate > 0.0:
            relative_decline = (previous_rate - current_rate) / previous_rate
            if relative_decline >= 0.3:  # 30% relative decline threshold
                return [
                    {
                        "type": "CONVERSION_DROP",
                        "severity": "HIGH",
                        "title": "Conversion Rate Drop",
                        "description": f"Conversion rate dropped by {relative_decline * 100:.1f}% (from {previous_rate:.1f}% to {current_rate:.1f}%).",
                        "affected_zone": None,
                        "suggested_action": "Analyze checkout queues and POS delays",
                        "metric_value": float(round(current_rate, 2)),
                        "baseline_value": float(round(previous_rate, 2)),
                        "generated_at": evaluation_time,
                    }
                ]

        return []

    @classmethod
    def _detect_dead_zones(
        cls, sessions: Sequence[Any], evaluation_time: datetime
    ) -> list[dict[str, Any]]:
        """Promotes ConversionEngine opportunity loss zones into MEDIUM severity DEAD_ZONE anomalies."""
        opportunity_zones = ConversionEngine.analyze_opportunity_loss(sessions)
        dead_zones = []

        for z in opportunity_zones:
            dead_zones.append(
                {
                    "type": "DEAD_ZONE",
                    "severity": "MEDIUM",
                    "title": "Dead Zone Detected",
                    "description": f"Zone '{z['zone']}' has high average dwell time ({z['avg_dwell_ms']:.1f}ms) but low conversion ({z['conversion_rate']:.1f}%) and low billing progression ({z['billing_progression_rate']:.1f}%).",
                    "affected_zone": z["zone"],
                    "suggested_action": "Revamp zone layout or optimize product placement",
                    "metric_value": float(z["conversion_rate"]),
                    "baseline_value": float(z["billing_progression_rate"]),
                    "generated_at": evaluation_time,
                }
            )

        return dead_zones
