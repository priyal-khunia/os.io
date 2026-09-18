"""
Metrics Module
Computes performance and fairness metrics for disk scheduling algorithms:
  - seek_distance: Total cylinder travel
  - service_time: Total elapsed time based on realistic mechanical disk model (7200 RPM HDD)
  - throughput: Serviced requests per second
  - fairness: Jain's Fairness Index, variance, and standard deviation of request response times
  - response_time: Mean, min, max response time based on actual request arrival times
"""

import math
from typing import List, Dict, Any, Optional
import numpy as np


# Realistic Disk Mechanical Parameters (Standard 7,200 RPM drive)
SEEK_TIME_PER_CYLINDER_MS = 0.15   # Average seek time per cylinder traversed
BASE_SEEK_OVERHEAD_MS = 1.0        # Head acceleration / settling overhead per seek stroke
ROTATIONAL_LATENCY_MS = 4.17       # Half rotation at 7,200 RPM (60000 / 7200 / 2)
TRANSFER_TIME_MS = 0.5             # Sector transfer time


def calculate_jains_fairness(values: List[float]) -> float:
    """
    Computes Jain's Fairness Index for an array of positive values:
        J = (sum(x_i))^2 / (n * sum(x_i^2))
    Ranges from 1/n (worst fairness) to 1.0 (perfect fairness).
    """
    if not values:
        return 1.0
    n = len(values)
    if n == 1:
        return 1.0
    arr = np.array(values, dtype=float)
    sum_val = float(np.sum(arr))
    sum_sq = float(np.sum(arr ** 2))
    if sum_sq == 0:
        return 1.0
    j = (sum_val ** 2) / (n * sum_sq)
    return round(float(np.clip(j, 1.0 / n, 1.0)), 4)


def compute_metrics(
    algorithm_result: Dict[str, Any],
    original_requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Computes all 5 key metrics given the algorithm execution result.
    Tracks step-by-step elapsed time, individual request arrival times,
    completion times, response times, and Jain's fairness index.
    """
    seek_distance = algorithm_result.get("total_seek_distance", 0)
    steps = algorithm_result.get("steps", [])
    n = len(original_requests)

    if n == 0:
        return {
            "seek_distance": 0,
            "service_time_ms": 0.0,
            "throughput_req_per_sec": 0.0,
            "fairness_variance": 0.0,
            "fairness_std_dev": 0.0,
            "jains_fairness_index": 1.0,
            "mean_response_time_ms": 0.0,
            "wait_times_ms": [],
            "response_times_ms": [],
            "max_response_time_ms": 0.0,
            "min_response_time_ms": 0.0,
            "request_telemetry": []
        }

    # Normalize arrival times
    if arrival_times is None or len(arrival_times) != n:
        arrival_times = [0.0] * n

    # Create request pool with arrival tracking (handles duplicates gracefully)
    pending_pool = [
        {
            "id": f"R{i + 1}",
            "cylinder": original_requests[i],
            "arrival_time": float(arrival_times[i]),
            "serviced": False,
            "completion_time": 0.0,
            "response_time": 0.0,
            "wait_time": 0.0
        }
        for i in range(n)
    ]

    current_time_ms = 0.0
    serviced_records = []

    for step in steps:
        dist = step.get("distance", 0)
        # Seek stroke time for this leg
        leg_seek_time = (dist * SEEK_TIME_PER_CYLINDER_MS + BASE_SEEK_OVERHEAD_MS) if dist > 0 else 0.0
        current_time_ms += leg_seek_time

        if step.get("is_serviced", False):
            # Rotational latency + sector transfer
            current_time_ms += (ROTATIONAL_LATENCY_MS + TRANSFER_TIME_MS)
            cyl = step["cylinder"]

            # Match to earliest unserviced request at this cylinder
            candidates = [req for req in pending_pool if not req["serviced"] and req["cylinder"] == cyl]
            if candidates:
                # Pick request with earliest arrival time
                chosen = min(candidates, key=lambda r: r["arrival_time"])
                chosen["serviced"] = True
                chosen["completion_time"] = round(current_time_ms, 2)
                resp_time = max(0.0, current_time_ms - chosen["arrival_time"])
                chosen["response_time"] = round(resp_time, 2)
                wait_time = max(0.0, resp_time - (ROTATIONAL_LATENCY_MS + TRANSFER_TIME_MS))
                chosen["wait_time"] = round(wait_time, 2)
                serviced_records.append(chosen)

    # In case any request remained unmatched, match in order
    for req in pending_pool:
        if not req["serviced"]:
            req["completion_time"] = round(current_time_ms, 2)
            resp = max(0.0, current_time_ms - req["arrival_time"])
            req["response_time"] = round(resp, 2)
            req["wait_time"] = round(max(0.0, resp - (ROTATIONAL_LATENCY_MS + TRANSFER_TIME_MS)), 2)
            serviced_records.append(req)

    total_service_time_ms = round(current_time_ms, 2)
    service_time_sec = total_service_time_ms / 1000.0
    throughput = round(n / service_time_sec, 2) if service_time_sec > 0 else 0.0

    # Response times across all requests
    response_times = [r["response_time"] for r in serviced_records]
    wait_times = [r["completion_time"] for r in serviced_records]

    mean_resp = round(float(np.mean(response_times)), 2) if response_times else 0.0
    min_resp = round(float(np.min(response_times)), 2) if response_times else 0.0
    max_resp = round(float(np.max(response_times)), 2) if response_times else 0.0

    # Fairness calculations
    fairness_variance = round(float(np.var(response_times)), 2) if len(response_times) > 1 else 0.0
    fairness_std_dev = round(float(np.std(response_times)), 2) if len(response_times) > 1 else 0.0
    jains_index = calculate_jains_fairness(response_times)

    return {
        "seek_distance": seek_distance,
        "service_time_ms": total_service_time_ms,
        "throughput_req_per_sec": throughput,
        "fairness_variance": fairness_variance,
        "fairness_std_dev": fairness_std_dev,
        "jains_fairness_index": jains_index,
        "mean_response_time_ms": mean_resp,
        "min_response_time_ms": min_resp,
        "max_response_time_ms": max_resp,
        "response_times": response_times,
        "response_times_ms": response_times,
        "wait_times_ms": wait_times,
        "request_telemetry": serviced_records
    }


def compare_all_metrics(
    requests: List[int],
    initial_head: int,
    disk_size: int = 200,
    direction: str = "UP",
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Runs all 4 algorithms on the same input and computes metrics for each.
    """
    from disk_scheduler.algorithms import fcfs, sstf, scan, c_scan

    algos = {
        "FCFS": fcfs(requests, initial_head, disk_size, direction),
        "SSTF": sstf(requests, initial_head, disk_size, direction),
        "SCAN": scan(requests, initial_head, disk_size, direction),
        "C-SCAN": c_scan(requests, initial_head, disk_size, direction),
    }

    comparison: Dict[str, Any] = {}
    for name, res in algos.items():
        metrics = compute_metrics(res, requests, initial_head, disk_size, arrival_times=arrival_times)
        comparison[name] = {
            "result": res,
            "metrics": metrics
        }

    return comparison
