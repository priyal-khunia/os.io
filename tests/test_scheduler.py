"""
Unit Tests for Disk Scheduling Simulator
"""

import pytest
from disk_scheduler.algorithms import fcfs, sstf, scan, c_scan, run_algorithm
from disk_scheduler.workload_generator import generate_workload
from disk_scheduler.classifier import (
    extract_features, classify_workload, predict_best_algorithm,
    generate_workload_description
)
from disk_scheduler.metrics import compute_metrics, compare_all_metrics


# Canonical textbook queue
CANONICAL_QUEUE = [98, 183, 37, 122, 14, 124, 65, 67]
CANONICAL_HEAD = 53
DISK_SIZE = 200


def test_fcfs_canonical():
    res = fcfs(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE)
    assert res["total_seek_distance"] == 640
    assert res["seek_order"] == CANONICAL_QUEUE
    assert res["head_movement_sequence"] == [53] + CANONICAL_QUEUE


def test_sstf_canonical():
    res = sstf(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE)
    assert res["total_seek_distance"] == 236
    assert res["seek_order"] == [65, 67, 37, 14, 98, 122, 124, 183]


def test_scan_canonical_up():
    res = scan(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="UP")
    # 53 -> 65 -> 67 -> 98 -> 122 -> 124 -> 183 -> 199 -> 37 -> 14
    # Distance: (199 - 53) + (199 - 14) = 146 + 185 = 331
    assert res["total_seek_distance"] == 331
    assert res["seek_order"] == [65, 67, 98, 122, 124, 183, 37, 14]
    assert 199 in res["head_movement_sequence"]


def test_scan_canonical_down():
    res = scan(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="DOWN")
    # 53 -> 37 -> 14 -> 0 -> 65 -> 67 -> 98 -> 122 -> 124 -> 183
    # Distance: (53 - 0) + (183 - 0) = 53 + 183 = 236
    assert res["total_seek_distance"] == 236
    assert res["seek_order"] == [37, 14, 65, 67, 98, 122, 124, 183]
    assert 0 in res["head_movement_sequence"]


def test_c_scan_canonical_up():
    res = c_scan(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="UP")
    # 53 -> 65 -> 67 -> 98 -> 122 -> 124 -> 183 -> 199 -> 0 -> 14 -> 37
    # Distance: (199 - 53) + 199 + 37 = 146 + 199 + 37 = 382
    assert res["total_seek_distance"] == 382
    assert res["seek_order"] == [65, 67, 98, 122, 124, 183, 14, 37]
    assert 199 in res["head_movement_sequence"]
    assert 0 in res["head_movement_sequence"]


def test_workload_generators():
    for pattern in ["random", "sequential", "clustered", "bursty"]:
        data = generate_workload(pattern=pattern, count=25, disk_size=200, seed=42)
        assert len(data["requests"]) == 25
        assert all(0 <= r < 200 for r in data["requests"])


def test_workload_descriptions():
    desc_seq = generate_workload_description("sequential")
    assert "consecutive" in desc_seq.lower() or "ordered" in desc_seq.lower()

    desc_clust = generate_workload_description("clustered")
    assert "localized" in desc_clust.lower() or "hotspot" in desc_clust.lower()

    desc_burst = generate_workload_description("bursty")
    assert "jump" in desc_burst.lower() or "burst" in desc_burst.lower()

    desc_rand = generate_workload_description("random")
    assert "scattered" in desc_rand.lower() or "spread" in desc_rand.lower()


def test_classifier_and_features():
    features = extract_features(CANONICAL_QUEUE, disk_size=200, initial_head=53)
    assert 0.0 <= features["spread"] <= 1.0
    assert 0.0 <= features["density"] <= 1.0
    assert 0.0 <= features["clustering"] <= 1.0
    assert 0.0 <= features["direction_bias"] <= 1.0

    cls_res = classify_workload(CANONICAL_QUEUE, disk_size=200, initial_head=53)
    assert cls_res["workload_type"] in ["random", "sequential", "clustered", "bursty"]
    assert "confidence" in cls_res
    assert sum(cls_res["probabilities"].values()) == pytest.approx(1.0, rel=1e-2)


def test_ml_classifier_module():
    from disk_scheduler.ml_model import predict_ml_algorithm, load_ml_model
    model = load_ml_model()
    assert model is not None
    features = {"spread": 0.82, "density": 0.65, "clustering": 0.88, "direction_bias": 0.25}
    pred = predict_ml_algorithm(features)
    assert pred["ml_predicted_algorithm"] in ["FCFS", "SSTF", "SCAN", "C-SCAN"]
    assert 0.0 <= pred["confidence"] <= 1.0
    assert len(pred["probabilities"]) > 0
    assert pred["model_loaded"] is True


def test_predict_best_algorithm():
    pred = predict_best_algorithm(CANONICAL_QUEUE, initial_head=53, disk_size=200, direction="UP")
    # In canonical queue with direction UP, SSTF has seek distance 236 which is minimum!
    assert pred["predicted_algorithm"] == "SSTF"
    assert pred["min_seek_distance"] == 236


def test_metrics_computation():
    res = sstf(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE)
    metrics = compute_metrics(res, CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE)
    assert metrics["seek_distance"] == 236
    assert metrics["service_time_ms"] > 0
    assert metrics["throughput_req_per_sec"] > 0
    assert metrics["fairness_variance"] >= 0
    assert metrics["mean_response_time_ms"] > 0


def test_compare_all_metrics():
    comp = compare_all_metrics(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="UP")
    assert set(comp.keys()) == {"FCFS", "SSTF", "SCAN", "C-SCAN"}
    assert comp["FCFS"]["metrics"]["seek_distance"] == 640
    assert comp["SSTF"]["metrics"]["seek_distance"] == 236
    assert comp["SCAN"]["metrics"]["seek_distance"] == 331
    assert comp["C-SCAN"]["metrics"]["seek_distance"] == 382


def test_empty_requests():
    empty_res = fcfs([], 50, 200)
    assert empty_res["total_seek_distance"] == 0
    assert empty_res["seek_order"] == []
    metrics = compute_metrics(empty_res, [], 50, 200)
    assert metrics["seek_distance"] == 0
    assert metrics["throughput_req_per_sec"] == 0.0


def test_arrival_patterns_generation():
    from disk_scheduler.workload_generator import generate_arrival_times
    for pattern in ["all_at_once", "sequential", "random", "bursty", "continuous"]:
        times = generate_arrival_times(20, pattern, seed=42)
        assert len(times) == 20
        # Times should be non-decreasing
        assert all(times[i] <= times[i+1] for i in range(len(times)-1))
        if pattern == "all_at_once":
            assert all(t == 0.0 for t in times)
        else:
            assert times[-1] > 0.0


def test_workload_generator_with_arrival_patterns():
    from disk_scheduler.workload_generator import generate_workload
    for arr_pat in ["all_at_once", "sequential", "random", "bursty", "continuous"]:
        res = generate_workload(pattern="clustered", count=15, disk_size=200, arrival_pattern=arr_pat, seed=10)
        assert len(res["requests"]) == 15
        assert len(res["arrival_times"]) == 15
        assert len(res["request_objects"]) == 15
        assert res["arrival_pattern"] == arr_pat
        assert res["request_objects"][0]["id"] == "R1"


def test_event_types_in_steps():
    # SCAN should record BOUNDARY_TURNAROUND or BOUNDARY
    scan_res = scan(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="UP")
    event_types = [step.get("event_type") for step in scan_res["steps"]]
    assert "SERVICED" in event_types
    assert "BOUNDARY_TURNAROUND" in event_types

    # C-SCAN should record CIRCULAR_RESET
    cscan_res = c_scan(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, direction="UP")
    cscan_events = [step.get("event_type") for step in cscan_res["steps"]]
    assert "SERVICED" in cscan_events
    assert "CIRCULAR_RESET" in cscan_events


def test_edge_case_duplicate_requests():
    dups = [50, 50, 50, 80, 80]
    res_fcfs = fcfs(dups, 50, 200)
    assert res_fcfs["total_seek_distance"] == 30  # 50->50(0)->50(0)->50(0)->80(30)->80(0)
    assert len(res_fcfs["seek_order"]) == 5

    res_sstf = sstf(dups, 50, 200)
    assert res_sstf["total_seek_distance"] == 30
    assert len(res_sstf["seek_order"]) == 5


def test_edge_case_head_at_boundaries():
    # Head at 0
    res_at_zero = scan([50, 100, 150], 0, 200, direction="UP")
    assert res_at_zero["seek_order"] == [50, 100, 150]
    assert res_at_zero["total_seek_distance"] == 150

    # Head at max cylinder 199
    res_at_max = scan([50, 100, 150], 199, 200, direction="DOWN")
    assert res_at_max["seek_order"] == [150, 100, 50]
    assert res_at_max["total_seek_distance"] == 149


def test_edge_case_all_requests_one_side():
    # All requests above head
    res_above = scan([80, 90, 100], 50, 200, direction="UP")
    assert res_above["seek_order"] == [80, 90, 100]

    # All requests below head
    res_below = scan([20, 30, 40], 50, 200, direction="DOWN")
    assert res_below["seek_order"] == [40, 30, 20]


def test_edge_case_single_request():
    for algo_fn in [fcfs, sstf, scan, c_scan]:
        res = algo_fn([100], 50, 200, direction="UP")
        assert len(res["seek_order"]) == 1
        assert res["seek_order"][0] == 100
        assert res["total_seek_distance"] == 50


def test_edge_case_head_on_request():
    res = sstf([50, 60], 50, 200)
    assert res["seek_order"] == [50, 60]
    assert res["total_seek_distance"] == 10


def test_jains_fairness_index_bounds():
    from disk_scheduler.metrics import calculate_jains_fairness

    # Equal response times -> perfectly fair (J = 1.0)
    assert calculate_jains_fairness([10.0, 10.0, 10.0, 10.0]) == pytest.approx(1.0, rel=1e-3)

    # Skewed response times -> lower fairness
    j_skew = calculate_jains_fairness([1.0, 1.0, 1.0, 100.0])
    assert 0.25 <= j_skew < 1.0

    # Minimum theoretical bound is 1/N
    n = 10
    extreme_skew = [0.0001] * (n - 1) + [1000.0]
    j_min = calculate_jains_fairness(extreme_skew)
    assert j_min >= (1.0 / n) - 0.01

    # Empty list
    assert calculate_jains_fairness([]) == 1.0


def test_metrics_with_real_arrival_times():
    arrival_times = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    res = fcfs(CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE)
    metrics = compute_metrics(res, CANONICAL_QUEUE, CANONICAL_HEAD, DISK_SIZE, arrival_times=arrival_times)
    assert "jains_fairness_index" in metrics
    assert 0.0 <= metrics["jains_fairness_index"] <= 1.0
    assert "response_times" in metrics
    assert len(metrics["response_times"]) == len(CANONICAL_QUEUE)
    # Each response time must be non-negative
    assert all(r >= 0 for r in metrics["response_times"])


def test_rule_based_recommendation():
    from disk_scheduler.classifier import recommend_rule_based_algorithm

    # Very short queue -> FCFS
    rec_short = recommend_rule_based_algorithm([40, 50], initial_head=30, disk_size=200)
    assert rec_short["recommended_algorithm"] == "FCFS"

    # Clustered hotspot -> SSTF
    rec_clust = recommend_rule_based_algorithm([50, 51, 52, 53, 50, 52, 51, 53, 52, 50], initial_head=50, disk_size=200)
    assert rec_clust["recommended_algorithm"] == "SSTF"

    # Continuous arrival with wide spread -> C-SCAN or SCAN
    wide_reqs = [5, 190, 12, 175, 25, 160, 40, 140, 60, 120, 80, 100, 15, 185, 30, 170, 45, 155, 65, 135, 85, 115]
    rec_wide = recommend_rule_based_algorithm(wide_reqs, initial_head=100, disk_size=200, arrival_pattern="continuous")
    assert rec_wide["recommended_algorithm"] in ["C-SCAN", "SCAN"]
