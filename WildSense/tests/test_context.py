"""Contextual adaptation tests: risk level in, legal polling interval out."""

from __future__ import annotations

import pytest

from context.risk import (
    DEFAULT_INTERVALS,
    MockExternalRiskProvider,
    PollingPolicy,
    RiskLevel,
    StaticRiskProvider,
    build_risk_provider,
)
from core.contracts import Event, EventType


def detection(timestamp: float) -> Event:
    return Event(
        timestamp=timestamp,
        event_type=EventType.SPIKE,
        confidence=0.9,
        temperature_c=40.0,
        humidity_pct=20.0,
    )


class TestRiskLevel:
    def test_levels_are_ordered(self):
        ranks = [level.rank for level in RiskLevel.ordered()]
        assert ranks == sorted(ranks)
        assert RiskLevel.EXTREME.rank > RiskLevel.LOW.rank

    def test_parse_accepts_strings_and_members(self):
        assert RiskLevel.parse("high") is RiskLevel.HIGH
        assert RiskLevel.parse(" HIGH ") is RiskLevel.HIGH
        assert RiskLevel.parse(RiskLevel.LOW) is RiskLevel.LOW

    def test_unknown_level_falls_back_rather_than_crashing(self):
        assert RiskLevel.parse("catastrophic") is RiskLevel.MODERATE

    def test_from_rank_clamps_out_of_range_values(self):
        assert RiskLevel.from_rank(-5) is RiskLevel.LOW
        assert RiskLevel.from_rank(99) is RiskLevel.EXTREME


class TestPollingPolicy:
    def test_high_risk_polls_faster_than_low_risk(self):
        policy = PollingPolicy()
        assert policy.interval_for(RiskLevel.EXTREME) < policy.interval_for(RiskLevel.HIGH)
        assert policy.interval_for(RiskLevel.HIGH) < policy.interval_for(RiskLevel.LOW)

    def test_config_intervals_override_the_defaults(self):
        policy = PollingPolicy(intervals={"low": 45.0, "extreme": 3.0})
        assert policy.interval_for(RiskLevel.LOW) == 45.0
        assert policy.interval_for(RiskLevel.EXTREME) == 3.0
        # Untouched levels keep their defaults.
        assert policy.interval_for(RiskLevel.HIGH) == DEFAULT_INTERVALS[RiskLevel.HIGH]

    def test_the_sensor_floor_wins_over_config(self):
        """A DHT22 must never be polled faster than 2s, whatever config says."""
        policy = PollingPolicy(
            intervals={"extreme": 0.1, "high": 0.5},
            sensor_min_interval_s=2.0,
        )
        assert policy.interval_for(RiskLevel.EXTREME) == 2.0
        assert policy.interval_for(RiskLevel.HIGH) == 2.0

    def test_every_level_respects_the_floor(self):
        policy = PollingPolicy(
            intervals={level.value: 0.01 for level in RiskLevel.ordered()},
            sensor_min_interval_s=2.0,
        )
        assert all(policy.interval_for(level) >= 2.0 for level in RiskLevel.ordered())

    def test_max_interval_stops_a_node_going_silent(self):
        policy = PollingPolicy(intervals={"low": 99999.0}, max_interval_s=120.0)
        assert policy.interval_for(RiskLevel.LOW) == 120.0

    def test_synthetic_sensor_has_no_floor_so_config_is_honoured(self):
        policy = PollingPolicy(intervals={"extreme": 0.25}, sensor_min_interval_s=0.0)
        assert policy.interval_for(RiskLevel.EXTREME) == 0.25


class TestStaticProvider:
    def test_returns_the_configured_level(self):
        provider = StaticRiskProvider(level="high")
        assessment = provider.assess([])
        assert assessment.level is RiskLevel.HIGH
        assert assessment.source == "static"
        assert 0.0 <= assessment.score <= 1.0

    def test_is_stable_across_calls(self):
        provider = StaticRiskProvider(level="low")
        assert {provider.assess([]).level for _ in range(10)} == {RiskLevel.LOW}


class TestMockExternalProvider:
    def test_assessment_is_well_formed(self):
        provider = MockExternalRiskProvider(seed=1)
        assessment = provider.assess([])
        assert assessment.level in RiskLevel.ordered()
        assert 0.0 <= assessment.score <= 1.0
        assert assessment.source == "mock_external"
        assert assessment.to_dict()["level"] == assessment.level.value

    def test_recent_detections_escalate_the_risk(self):
        """The closed loop: detections raise risk, which shortens the interval."""
        clock = {"t": 1000.0}
        provider = MockExternalRiskProvider(
            base_level="low",
            events_for_escalation=2,
            event_window_s=90.0,
            seed=3,
            clock=lambda: clock["t"],
        )

        calm = provider.assess([])
        busy = provider.assess([detection(clock["t"] - 5.0) for _ in range(6)])

        assert busy.level.rank > calm.level.rank
        assert "escalated" in busy.reason

    def test_stale_detections_do_not_escalate(self):
        clock = {"t": 1000.0}
        provider = MockExternalRiskProvider(
            base_level="low", event_window_s=60.0, seed=3, clock=lambda: clock["t"]
        )

        calm = provider.assess([])
        # Detections from an hour ago are history, not context.
        stale = provider.assess([detection(clock["t"] - 3600.0) for _ in range(6)])
        assert stale.level.rank == calm.level.rank

    def test_the_ambient_forecast_moves_over_time(self):
        clock = {"t": 0.0}
        provider = MockExternalRiskProvider(
            base_level="low", cycle_seconds=100.0, seed=4, clock=lambda: clock["t"]
        )

        levels = set()
        for offset in range(0, 100, 5):
            clock["t"] = float(offset)
            levels.add(provider.assess([]).level)
        assert len(levels) > 1, "a static 'forecast' would make the demo pointless"

    def test_risk_never_exceeds_the_top_band(self):
        clock = {"t": 500.0}
        provider = MockExternalRiskProvider(
            base_level="high", events_for_escalation=1, seed=5, clock=lambda: clock["t"]
        )
        assessment = provider.assess([detection(clock["t"]) for _ in range(50)])
        assert assessment.level is RiskLevel.EXTREME
        assert assessment.score <= 1.0


class TestProviderFactory:
    def test_builds_both_provider_kinds(self):
        assert isinstance(build_risk_provider("static", {"level": "low"}), StaticRiskProvider)
        assert isinstance(build_risk_provider("mock_external", {}), MockExternalRiskProvider)

    def test_unknown_provider_is_a_clear_error(self):
        with pytest.raises(ValueError, match="unknown risk provider"):
            build_risk_provider("satellite-feed", {})


class TestEndToEndAdaptation:
    def test_risk_changes_translate_into_interval_changes(self):
        policy = PollingPolicy(
            intervals={"low": 60.0, "moderate": 30.0, "high": 5.0, "extreme": 2.0},
            sensor_min_interval_s=2.0,
        )
        intervals = [
            policy.interval_for_assessment(StaticRiskProvider(level=level.value).assess([]))
            for level in RiskLevel.ordered()
        ]
        assert intervals == [60.0, 30.0, 5.0, 2.0]
        assert intervals == sorted(intervals, reverse=True)
