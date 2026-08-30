"""Federation tests -- FedAvg arithmetic, local training, and real rounds.

The averaging tests check exact numbers rather than "it ran": a silently wrong
weighted mean is the kind of bug that still produces a plausible-looking loss
curve.
"""

from __future__ import annotations

import pytest
import torch

from core.contracts import EventType, Reading
from detectors.model import EventClassifier
from federation.averager import FederatedAverager, NodeUpdate, weighted_average
from federation.local_trainer import LocalTrainer
from federation.simulation import FederationSimulation, NodeSpec


def state(value: float, bias: float | None = None) -> dict[str, torch.Tensor]:
    """A tiny two-key state dict, easy to check by hand."""
    return {
        "w": torch.tensor([value, value * 2.0]),
        "b": torch.tensor([bias if bias is not None else value]),
    }


# ---------------------------------------------------------------------------
# The averaging arithmetic
# ---------------------------------------------------------------------------


class TestWeightedAverage:
    def test_equal_sample_counts_give_the_plain_mean(self):
        merged = weighted_average(
            [
                NodeUpdate("a", 100, 0.0, state(10.0)),
                NodeUpdate("b", 100, 0.0, state(20.0)),
            ]
        )
        assert merged["w"].tolist() == pytest.approx([15.0, 30.0])
        assert merged["b"].tolist() == pytest.approx([15.0])

    def test_sample_counts_actually_weight_the_result(self):
        # 3:1 split -> 0.75 * 10 + 0.25 * 20 = 12.5
        merged = weighted_average(
            [
                NodeUpdate("a", 300, 0.0, state(10.0)),
                NodeUpdate("b", 100, 0.0, state(20.0)),
            ]
        )
        assert merged["w"][0].item() == pytest.approx(12.5)
        assert merged["w"][1].item() == pytest.approx(25.0)

    def test_three_nodes_match_the_hand_computed_mean(self):
        updates = [
            NodeUpdate("a", 50, 0.0, state(1.0)),
            NodeUpdate("b", 150, 0.0, state(3.0)),
            NodeUpdate("c", 200, 0.0, state(7.0)),
        ]
        total = 400
        expected = (1.0 * 50 + 3.0 * 150 + 7.0 * 200) / total
        merged = weighted_average(updates)
        assert merged["w"][0].item() == pytest.approx(expected)

    def test_a_zero_sample_node_contributes_nothing(self):
        merged = weighted_average(
            [
                NodeUpdate("a", 100, 0.0, state(4.0)),
                NodeUpdate("idle", 0, 0.0, state(1000.0)),
            ]
        )
        assert merged["w"][0].item() == pytest.approx(4.0)

    def test_empty_and_degenerate_inputs_raise(self):
        with pytest.raises(ValueError):
            weighted_average([])
        with pytest.raises(ValueError):
            weighted_average([NodeUpdate("a", 0, 0.0, state(1.0))])

    def test_mismatched_architectures_are_rejected(self):
        good = NodeUpdate("a", 10, 0.0, state(1.0))
        odd = NodeUpdate("b", 10, 0.0, {"w": torch.tensor([1.0, 2.0])})  # missing "b"
        with pytest.raises(ValueError, match="different"):
            weighted_average([good, odd])

    def test_real_model_state_dicts_average_key_by_key(self):
        left, right = EventClassifier(window=16, hidden=8), EventClassifier(window=16, hidden=8)
        merged = weighted_average(
            [
                NodeUpdate("l", 1, 0.0, left.state_dict()),
                NodeUpdate("r", 1, 0.0, right.state_dict()),
            ]
        )
        assert set(merged) == set(left.state_dict())
        for key in merged:
            expected = (left.state_dict()[key] + right.state_dict()[key]) / 2.0
            assert torch.allclose(merged[key], expected, atol=1e-6)

        # And the merged weights load cleanly back into the same architecture.
        EventClassifier(window=16, hidden=8).load_state_dict(merged)


class TestFederatedAverager:
    def test_aggregation_waits_for_the_quorum(self):
        averager = FederatedAverager(min_updates=3)
        averager.submit("a", state(1.0), 10)
        averager.submit("b", state(3.0), 10)

        assert averager.aggregate() is None, "should defer below the quorum"
        assert averager.round_number == 0
        assert averager.pending_count == 2, "deferred updates must stay pending"

        averager.submit("c", state(5.0), 10)
        assert averager.aggregate() is not None
        assert averager.round_number == 1

    def test_aggregate_clears_pending_so_rounds_do_not_bleed(self):
        averager = FederatedAverager(min_updates=1)
        averager.submit("a", state(10.0), 10)
        averager.aggregate()
        assert averager.pending_count == 0

        averager.submit("a", state(20.0), 10)
        merged = averager.aggregate()
        assert merged["w"][0].item() == pytest.approx(20.0), "round 1 must not linger"

    def test_history_and_round_numbers_advance(self):
        averager = FederatedAverager(min_updates=2)
        for round_index in range(3):
            averager.submit("a", state(float(round_index)), 20, loss=0.5)
            averager.submit("b", state(float(round_index)), 20, loss=0.3)
            averager.aggregate()

        assert averager.round_number == 3
        history = averager.history
        assert [entry["round"] for entry in history] == [1, 2, 3]
        assert history[0]["total_samples"] == 40
        assert history[0]["mean_local_loss"] == pytest.approx(0.4)

    def test_seeding_installs_weights_without_counting_a_round(self):
        averager = FederatedAverager(min_updates=1)
        averager.seed(state(42.0))

        assert averager.round_number == 0, "seeding is not a round"
        assert averager.global_weights()["w"][0].item() == pytest.approx(42.0)

    def test_seeded_weights_are_copied_not_aliased(self):
        averager = FederatedAverager(min_updates=1)
        original = state(1.0)
        averager.seed(original)
        original["w"] += 100.0
        assert averager.global_weights()["w"][0].item() == pytest.approx(1.0)

    def test_submitted_weights_are_copied_not_aliased(self):
        averager = FederatedAverager(min_updates=1)
        original = state(1.0)
        averager.submit("a", original, 10)
        original["w"] += 100.0  # mutate after submitting

        merged = averager.aggregate()
        assert merged["w"][0].item() == pytest.approx(1.0)

    def test_concurrent_submits_are_all_recorded(self):
        from concurrent.futures import ThreadPoolExecutor

        averager = FederatedAverager(min_updates=20)
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: averager.submit(f"n{i}", state(float(i)), 10), range(20)))
        assert averager.pending_count == 20
        assert averager.aggregate() is not None


# ---------------------------------------------------------------------------
# Local training
# ---------------------------------------------------------------------------


def labelled_reading(temperature: float, humidity: float) -> Reading:
    return Reading(timestamp=0.0, temperature_c=temperature, humidity_pct=humidity, source="t")


class TestLocalTrainer:
    def test_a_window_is_only_stored_once_it_is_full(self):
        trainer = LocalTrainer(node_id="n", window_size=8)
        completions = [
            trainer.observe(labelled_reading(20.0 + i, 50.0), EventType.NONE) for i in range(10)
        ]
        assert completions[:7] == [False] * 7
        assert completions[7] is True
        assert trainer.buffered_samples == 3

    def test_incomplete_readings_are_skipped(self):
        trainer = LocalTrainer(node_id="n", window_size=4)
        partial = Reading(timestamp=0.0, temperature_c=20.0, humidity_pct=None, source="t")
        assert trainer.observe(partial, EventType.NONE) is False
        assert trainer.buffered_samples == 0

    def test_buffers_are_bounded_and_per_class(self):
        trainer = LocalTrainer(node_id="n", window_size=4, per_class_capacity=5)
        for index in range(200):
            trainer.observe(labelled_reading(20.0 + index * 0.1, 50.0), EventType.SPIKE)
        assert trainer.class_counts["spike"] == 5
        assert trainer.buffered_samples == 5

    def test_not_ready_with_a_single_class(self):
        trainer = LocalTrainer(node_id="n", window_size=4, min_samples=5)
        for index in range(60):
            trainer.observe(labelled_reading(20.0 + index * 0.1, 50.0), EventType.NONE)
        assert trainer.ready() is False, "one class alone teaches the model nothing"

        for index in range(60):
            trainer.observe(labelled_reading(40.0 + index * 0.5, 20.0), EventType.SPIKE)
        assert trainer.ready() is True

    def test_observe_stream_reads_labels_from_sensor_metadata(self):
        from sensors.synthetic import SyntheticEnvSensor

        sensor = SyntheticEnvSensor(seed=5, anomaly_probability=0.15, quiet_samples=5)
        trainer = LocalTrainer(node_id="n", window_size=16)
        trainer.observe_stream(sensor.stream(400))

        assert trainer.buffered_samples > 0
        assert trainer.class_counts["none"] > 0
        assert sum(trainer.class_counts.values()) == trainer.buffered_samples

    def test_local_fit_reduces_loss_on_its_own_data(self):
        from sensors.synthetic import SyntheticEnvSensor

        sensor = SyntheticEnvSensor(seed=3, anomaly_probability=0.2, quiet_samples=4)
        trainer = LocalTrainer(node_id="n", window_size=16, hidden=16, epochs=12, seed=1)
        trainer.observe_stream(sensor.stream(900))
        assert trainer.ready()

        windows, labels = trainer.dataset()
        loss_before, _ = trainer.evaluate(windows, labels)
        result = trainer.fit()
        loss_after, accuracy_after = trainer.evaluate(windows, labels)

        assert loss_after < loss_before, "local training must actually learn"
        assert result.num_samples == windows.shape[0]
        assert accuracy_after > 0.5

    def test_fit_on_an_empty_buffer_is_a_no_op(self):
        trainer = LocalTrainer(node_id="n", window_size=8)
        result = trainer.fit()
        assert result.num_samples == 0
        assert result.epochs == 0

    def test_weights_round_trip_without_aliasing(self):
        trainer = LocalTrainer(node_id="n", window_size=8, hidden=8)
        weights = trainer.get_weights()
        key = next(iter(weights))
        weights[key] += 5.0  # mutate the copy

        trainer.set_weights(trainer.get_weights())  # unaffected by the mutation
        assert not torch.allclose(trainer.get_weights()[key], weights[key])


# ---------------------------------------------------------------------------
# The full simulation
# ---------------------------------------------------------------------------


def small_simulation(**overrides) -> FederationSimulation:
    """A deliberately tiny simulation so the suite stays fast.

    Seeds the global torch RNG so model initialisation is reproducible
    regardless of what earlier tests did to it -- `train_model` calls
    `torch.manual_seed`, so test order would otherwise leak into results here.
    """
    torch.manual_seed(1234)
    options = dict(
        specs=[
            NodeSpec("node-a", profile="coastal", seed=11, anomaly_probability=0.18),
            NodeSpec("node-b", profile="arid", seed=22, anomaly_probability=0.18),
            NodeSpec("node-c", profile="alpine", seed=33, anomaly_probability=0.18),
        ],
        window_size=16,
        hidden=16,
        local_epochs=3,
        samples_per_round=200,
        warmup_readings=700,
        validation_samples_per_class=25,
    )
    options.update(overrides)
    return FederationSimulation(**options)


class TestFederationSimulation:
    def test_a_single_round_aggregates_every_node(self):
        simulation = small_simulation()
        result = simulation.run_round()

        assert result.aggregated is True
        assert result.round_number == 1
        assert len(result.node_results) == 3
        assert {item.node_id for item in result.node_results} == {"node-a", "node-b", "node-c"}
        assert result.total_samples > 0

    def test_nodes_have_genuinely_different_climates(self):
        simulation = small_simulation()
        simulation.prime()

        means = []
        for node in simulation.nodes:
            windows, _ = node.trainer.dataset()
            means.append(float(windows[:, :, 0].mean()))

        # arid ~33 C vs alpine ~6 C: the spread is the point of federating.
        assert max(means) - min(means) > 10.0

    def test_repeated_rounds_improve_the_global_model(self):
        """Federation must learn -- but not necessarily monotonically.

        FedAvg loss genuinely oscillates round to round: each node drifts
        toward its own climate during local epochs and averaging pulls them
        back, so any single round can be worse than the one before it. The
        claim worth testing is that the fleet is better after several rounds
        than after one, not that every round beats its predecessor.
        """
        simulation = small_simulation()
        results = simulation.run(rounds=6)

        assert all(result.aggregated for result in results)
        assert simulation.averager.round_number == 6

        first = results[0]
        best_recent_loss = min(result.global_loss for result in results[-3:])
        best_recent_accuracy = max(result.global_accuracy for result in results[-3:])

        assert best_recent_loss < first.global_loss, (
            f"global loss never improved on round 1 ({first.global_loss:.4f}); "
            f"best of the last three was {best_recent_loss:.4f}"
        )
        assert best_recent_accuracy > first.global_accuracy
        # Four balanced classes, so 0.25 is chance.
        assert best_recent_accuracy > 0.55

    def test_the_global_model_learns_more_than_one_class(self):
        simulation = small_simulation()
        simulation.run(rounds=4)
        weights = simulation.averager.global_weights()
        per_class = simulation.per_class_accuracy(weights)

        assert sum(1 for value in per_class.values() if value > 0.3) >= 2, (
            f"model collapsed onto a single class: {per_class}"
        )

    def test_on_round_callback_receives_result_and_weights(self):
        seen: list[tuple[int, int]] = []

        def callback(result, weights):
            seen.append((result.round_number, len(weights)))

        simulation = small_simulation(on_round=callback)
        simulation.run(rounds=2)

        assert [entry[0] for entry in seen] == [1, 2]
        assert all(entry[1] > 0 for entry in seen)

    def test_a_raising_callback_does_not_break_the_round(self):
        def explode(result, weights):
            raise RuntimeError("downstream consumer is broken")

        simulation = small_simulation(on_round=explode)
        result = simulation.run_round()
        assert result.aggregated is True

    def test_status_is_dashboard_ready(self):
        simulation = small_simulation()
        simulation.run_round()
        status = simulation.status()

        assert status["rounds_completed"] == 1
        assert len(status["nodes"]) == 3
        assert status["latest_round"]["aggregated"] is True
        assert {"round", "global_loss", "global_accuracy"} <= set(status["history"][0])

    def test_averaged_weights_load_into_the_live_detector(self):
        """Federation output must be directly usable by the detector."""
        from detectors.env_anomaly import EnvAnomalyDetector

        simulation = small_simulation()
        simulation.run_round()
        weights = simulation.averager.global_weights()

        detector = EnvAnomalyDetector(window_size=16, hidden=16, model_path=None)
        assert detector.set_weights(weights) is True
        assert detector.status()["model_ready"] is True

    def test_rejects_an_empty_node_list(self):
        with pytest.raises(ValueError):
            FederationSimulation(specs=[])

    def test_seeding_from_a_trained_model_beats_a_cold_start(self):
        """Round 1 must refine an existing model, not replace it with noise.

        Without seeding, the first aggregation averages three randomly
        initialised models and produces a chance-level global model -- which
        the live pipeline would then hot-swap over a perfectly good detector.
        """
        from detectors.train import train_model

        trained, metrics = train_model(
            profiles=["temperate"], samples_per_class=150, window=16, hidden=16,
            epochs=25, seed=0,
        )
        assert metrics["val_accuracy"] > 0.6, "the seed model itself must be good"

        cold = small_simulation()
        warm = small_simulation(initial_weights=trained.state_dict())

        cold_first = cold.run_round()
        warm_first = warm.run_round()

        assert warm_first.global_accuracy > cold_first.global_accuracy, (
            f"seeded round 1 ({warm_first.global_accuracy:.3f}) should beat "
            f"cold round 1 ({cold_first.global_accuracy:.3f})"
        )

    def test_seeded_nodes_start_from_the_seed_weights(self):
        seed_model = EventClassifier(window=16, hidden=16)
        simulation = small_simulation(initial_weights=seed_model.state_dict())

        installed = simulation.averager.global_weights()
        assert installed is not None
        assert simulation.averager.round_number == 0
        for key, value in seed_model.state_dict().items():
            assert torch.allclose(installed[key], value)
