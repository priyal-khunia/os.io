"""
Tests for Flask REST API endpoints
"""

import json
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "ok"


def test_generate_workload_endpoint(client):
    res = client.post("/api/generate-workload", json={
        "pattern": "clustered",
        "count": 15,
        "disk_size": 200,
        "seed": 123
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert data["pattern"] == "clustered"
    assert len(data["requests"]) == 15


def test_simulate_endpoint(client):
    res = client.post("/api/simulate", json={
        "requests": [98, 183, 37, 122, 14, 124, 65, 67],
        "initial_head": 53,
        "disk_size": 200,
        "direction": "UP",
        "algorithm": "FCFS"
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert data["total_seek_distance"] == 640
    assert "metrics" in data
    assert data["metrics"]["seek_distance"] == 640
    assert "classification" in data
    assert "ml_predicted_algorithm" in data
    assert "ml_prediction" in data
    assert data["ml_predicted_algorithm"] in ["FCFS", "SSTF", "SCAN", "C-SCAN"]


def test_classify_ml_endpoint(client):
    res = client.post("/api/classify", json={
        "requests": [98, 183, 37, 122, 14, 124, 65, 67],
        "initial_head": 53,
        "disk_size": 200,
        "direction": "UP"
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert "classification" in data
    assert "prediction" in data
    assert "ml_prediction" in data
    assert "ml_predicted_algorithm" in data
    assert data["ml_predicted_algorithm"] in ["FCFS", "SSTF", "SCAN", "C-SCAN"]
    assert "confidence" in data["ml_prediction"]
    assert "probabilities" in data["ml_prediction"]


def test_simulate_adaptive_endpoint(client):
    res = client.post("/api/simulate", json={
        "requests": [98, 183, 37, 122, 14, 124, 65, 67],
        "initial_head": 53,
        "disk_size": 200,
        "direction": "UP",
        "algorithm": "ADAPTIVE"
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert data["is_adaptive"] is True
    assert data["algorithm"] == "SSTF"
    assert data["total_seek_distance"] == 236
    assert data["adaptive_info"] is not None


def test_compare_endpoint(client):
    res = client.post("/api/compare", json={
        "requests": [98, 183, 37, 122, 14, 124, 65, 67],
        "initial_head": 53,
        "disk_size": 200,
        "direction": "UP"
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert "comparison" in data
    assert "ranking" in data
    assert data["ranking"][0]["algorithm"] in ["SSTF", "SCAN"]


def test_compare_all_workloads_endpoint(client):
    res = client.post("/api/compare-all-workloads", json={
        "count": 15,
        "disk_size": 200,
        "initial_head": 50,
        "direction": "UP",
        "seed": 42
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert "workload_benchmarks" in data
    bm = data["workload_benchmarks"]
    assert "random" in bm
    assert "sequential" in bm
    assert "clustered" in bm
    assert "bursty" in bm

    # Verify descriptions accurately reflect each pattern
    assert "consecutive" in bm["sequential"]["description"].lower() or "ordered" in bm["sequential"]["description"].lower()
    assert "localized" in bm["clustered"]["description"].lower() or "hotspot" in bm["clustered"]["description"].lower()
    assert "jump" in bm["bursty"]["description"].lower() or "burst" in bm["bursty"]["description"].lower()
    assert "scattered" in bm["random"]["description"].lower() or "spread" in bm["random"]["description"].lower()


def test_compare_arrival_patterns_endpoint(client):
    res = client.post("/api/compare-arrival-patterns", json={
        "spatial_pattern": "clustered",
        "count": 12,
        "disk_size": 200,
        "initial_head": 50,
        "direction": "UP",
        "seed": 42
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert "arrival_benchmarks" in data
    bm = data["arrival_benchmarks"]
    for pat in ["all_at_once", "sequential", "random", "bursty", "continuous"]:
        assert pat in bm
        assert "comparison" in bm[pat]
        assert "Adaptive" in bm[pat]["comparison"]
        assert "FCFS" in bm[pat]["comparison"]
        assert "SSTF" in bm[pat]["comparison"]
        assert "SCAN" in bm[pat]["comparison"]
        assert "C-SCAN" in bm[pat]["comparison"]


def test_simulate_with_arrival_data(client):
    res = client.post("/api/simulate", json={
        "requests": [10, 50, 90, 130],
        "arrival_times": [0.0, 5.0, 10.0, 15.0],
        "arrival_pattern": "continuous",
        "initial_head": 50,
        "disk_size": 200,
        "direction": "UP",
        "algorithm": "ADAPTIVE",
        "adaptive_basis": "RULE"
    })
    assert res.status_code == 200
    data = json.loads(res.data)["data"]
    assert data["is_adaptive"] is True
    assert "metrics" in data
    assert "jains_fairness_index" in data["metrics"]
    assert 0.0 <= data["metrics"]["jains_fairness_index"] <= 1.0
    assert "response_times" in data["metrics"]
    assert len(data["metrics"]["response_times"]) == 4
