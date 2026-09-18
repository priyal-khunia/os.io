"""
Classifier Module
Extracts queue features (spread, density, clustering, direction bias, plus extended metrics),
classifies workload type (random, sequential, clustered, bursty),
and provides both analytical rule-based recommendation and simulation-backed analysis.
"""

import math
from typing import List, Dict, Any, Optional
import numpy as np
from disk_scheduler.algorithms import fcfs, sstf, scan, c_scan


def extract_features(
    requests: List[int],
    disk_size: int = 200,
    initial_head: int = 50,
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Extracts statistical, spatial, and arrival features from a request queue:
      - spread: Normalized span and standard deviation of cylinder requests
      - density: Spatial concentration of requests per cylinder span
      - clustering: Spatial clumping / multi-cluster variance metric
      - direction_bias: Monotonic net flow and directional momentum
      - extended metrics: mean, std dev, queue length, inter-arrival time, burstiness, head distance
    """
    n = len(requests)
    if n == 0:
        return {
            "spread": 0.0,
            "density": 0.0,
            "clustering": 0.0,
            "direction_bias": 0.0,
            "mean_cylinder": 0.0,
            "std_dev": 0.0,
            "span": 0,
            "queue_length": 0,
            "avg_inter_arrival_time": 0.0,
            "burstiness_indicator": 0.0,
            "head_to_requests_dist": 0.0,
            "low_high_ratio": 0.5,
            "details": {
                "span": 0,
                "std_dev": 0.0,
                "mean_cylinder": 0.0,
                "mean_consecutive_diff": 0.0,
                "cv_diff": 0.0,
                "net_flow": 0.0,
                "head_bias": 0.0,
                "burst_jumps_count": 0,
                "head_to_requests_dist": 0.0
            }
        }

    arr = np.array(requests, dtype=float)
    min_cyl = float(np.min(arr))
    max_cyl = float(np.max(arr))
    span = max_cyl - min_cyl
    std_dev = float(np.std(arr))
    mean_cyl = float(np.mean(arr))

    # 1. Spread: Normalized range [0, 1] relative to disk size
    normalized_span = span / max(1, disk_size - 1)
    normalized_std = std_dev / (disk_size / 2.0)
    spread_score = float(np.clip(0.6 * normalized_span + 0.4 * normalized_std, 0.0, 1.0))

    # 2. Density: Requests per unit cylinder span and proximity
    if span > 0:
        spatial_density = n / (span + 1.0)
        density_score = float(np.clip(spatial_density * 2.0, 0.0, 1.0))
    else:
        spatial_density = float(n)
        density_score = 1.0

    # 3. Clustering: Spatial grouping using sorted differences
    sorted_reqs = np.sort(arr)
    sorted_diffs = np.diff(sorted_reqs) if len(sorted_reqs) > 1 else np.array([0.0])
    mean_diff = float(np.mean(sorted_diffs)) if len(sorted_diffs) > 0 else 0.0
    std_diff = float(np.std(sorted_diffs)) if len(sorted_diffs) > 0 else 0.0

    cv_diff = (std_diff / (mean_diff + 1e-6)) if mean_diff > 0 else 0.0
    clustering_score = float(np.clip(cv_diff / 2.5, 0.0, 1.0))

    # 4. Direction Bias: Net directional flow and monotonic transitions
    if n > 1:
        step_diffs = np.diff(arr)
        sum_abs_diffs = float(np.sum(np.abs(step_diffs)))
        sum_diffs = float(np.sum(step_diffs))
        net_flow = (sum_diffs / (sum_abs_diffs + 1e-6)) if sum_abs_diffs > 0 else 0.0
        
        pos_steps = np.sum(step_diffs > 0)
        neg_steps = np.sum(step_diffs < 0)
        dominant_step_ratio = max(pos_steps, neg_steps) / (n - 1)
        direction_bias_score = float(np.clip(0.6 * abs(net_flow) + 0.4 * dominant_step_ratio, 0.0, 1.0))

        big_jump_thresh = disk_size * 0.25
        burst_jumps_count = int(np.sum(np.abs(step_diffs) >= big_jump_thresh))
    else:
        net_flow = 0.0
        direction_bias_score = 0.0
        burst_jumps_count = 0

    # Head bias: requests >= head vs < head
    above_head = np.sum(arr >= initial_head)
    head_bias = float((above_head - (n - above_head)) / n)

    # Head to requests distance (mean distance)
    head_dists = np.abs(arr - initial_head)
    head_to_requests_dist = float(np.mean(head_dists))

    # Low/high cylinder concentration (relative to disk midpoint)
    midpoint = disk_size / 2.0
    low_half_count = np.sum(arr < midpoint)
    low_high_ratio = float(low_half_count / n)

    # Inter-arrival time analysis
    if arrival_times and len(arrival_times) > 1:
        arr_times = np.array(arrival_times, dtype=float)
        inter_arrival = np.diff(arr_times)
        avg_inter_arrival = float(np.mean(inter_arrival))
    else:
        avg_inter_arrival = 0.0

    burstiness_indicator = float(np.clip((burst_jumps_count / max(1, n - 1)) * 2.5, 0.0, 1.0))

    return {
        "spread": round(spread_score, 4),
        "density": round(density_score, 4),
        "clustering": round(clustering_score, 4),
        "direction_bias": round(direction_bias_score, 4),
        "mean_cylinder": round(mean_cyl, 2),
        "std_dev": round(std_dev, 2),
        "span": int(span),
        "queue_length": n,
        "avg_inter_arrival_time": round(avg_inter_arrival, 2),
        "burstiness_indicator": round(burstiness_indicator, 3),
        "head_to_requests_dist": round(head_to_requests_dist, 2),
        "low_high_ratio": round(low_high_ratio, 3),
        "details": {
            "span": int(span),
            "std_dev": round(std_dev, 2),
            "mean_cylinder": round(mean_cyl, 2),
            "mean_consecutive_diff": round(mean_diff, 2),
            "cv_diff": round(cv_diff, 3),
            "net_flow": round(net_flow, 3),
            "head_bias": round(head_bias, 3),
            "burst_jumps_count": burst_jumps_count,
            "head_to_requests_dist": round(head_to_requests_dist, 2)
        }
    }


def classify_workload(
    requests: List[int],
    disk_size: int = 200,
    initial_head: int = 50,
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Classifies the request pattern into one of: 'random', 'sequential', 'clustered', 'bursty'.
    Returns classification label, confidence scores for all classes, and explanatory reasons.
    """
    features = extract_features(requests, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
    
    if len(requests) <= 2:
        return {
            "workload_type": "random",
            "confidence": 0.5,
            "probabilities": {"random": 0.5, "sequential": 0.2, "clustered": 0.15, "bursty": 0.15},
            "features": features,
            "reason": "Request queue is too short for definitive classification."
        }

    spread = features["spread"]
    density = features["density"]
    clustering = features["clustering"]
    direction_bias = features["direction_bias"]
    details = features["details"]
    cv_diff = details["cv_diff"]
    burst_jumps = details["burst_jumps_count"]
    n = len(requests)

    # 1. Sequential score: high direction bias, very small consecutive differences
    step_diffs = np.abs(np.diff(np.array(requests, dtype=float)))
    small_steps = np.sum(step_diffs <= max(3, disk_size * 0.03))
    small_step_ratio = small_steps / max(1, len(step_diffs))
    
    seq_score = (
        0.45 * direction_bias +
        0.35 * small_step_ratio +
        0.20 * (1.0 - min(1.0, clustering))
    )
    if small_step_ratio > 0.7 and direction_bias > 0.6:
        seq_score += 0.3

    # 2. Clustered score: high CV of sorted diffs, high clustering, distinct spatial pockets
    clust_score = (
        0.55 * clustering +
        0.25 * (1.0 - direction_bias) +
        0.20 * min(1.0, density)
    )
    if cv_diff > 1.6:
        clust_score += 0.25

    # 3. Bursty score: small steps punctuated by large jumps across disk tracks
    jump_ratio = burst_jumps / max(1, n - 1)
    burst_score = (
        0.40 * min(1.0, jump_ratio * 4.0) +
        0.35 * small_step_ratio +
        0.25 * (1.0 - abs(details["net_flow"]))
    )
    if burst_jumps >= 1 and small_step_ratio >= 0.4:
        burst_score += 0.2

    # 4. Random score: uniform spread, moderate CV (~1.0), low net flow, low small step ratio
    rand_score = (
        0.45 * spread +
        0.30 * (1.0 - abs(details["net_flow"])) +
        0.25 * max(0.0, 1.0 - abs(cv_diff - 1.0))
    )

    raw_scores = np.array([rand_score, seq_score, clust_score, burst_score], dtype=float)
    exp_scores = np.exp(raw_scores * 3.5)
    probs = exp_scores / np.sum(exp_scores)

    patterns = ["random", "sequential", "clustered", "bursty"]
    best_idx = int(np.argmax(probs))
    predicted_type = patterns[best_idx]
    confidence = float(probs[best_idx])

    prob_dict = {pat: round(float(p), 4) for pat, p in zip(patterns, probs)}

    return {
        "workload_type": predicted_type,
        "confidence": round(confidence, 3),
        "probabilities": prob_dict,
        "features": features,
        "reason": generate_workload_description(predicted_type, features)
    }


def generate_workload_description(pattern_type: str, features: Optional[Dict[str, Any]] = None) -> str:
    """
    Generates an accurate, descriptive summary for a given workload pattern.
    """
    pat = (pattern_type or "random").lower().strip()
    f = features or {}
    spread = f.get("spread", 0.75)
    clustering = f.get("clustering", 0.6)
    direction_bias = f.get("direction_bias", 0.5)
    details = f.get("details", {})
    cv_diff = details.get("cv_diff", 1.2)
    burst_jumps = details.get("burst_jumps_count", 3)

    if pat == "sequential":
        return f"Ordered streaming pattern characterized by consecutive cylinder access (direction bias {direction_bias:.2f}, contiguous monotonic traversal)."
    elif pat == "clustered":
        return f"Localized grouping pattern concentrated in distinct cylinder hotspots (spatial clustering index {clustering:.2f}, CV: {cv_diff:.2f})."
    elif pat == "bursty":
        return f"Irregular pattern characterized by localized request bursts punctuated by {burst_jumps} sudden large jumps across distant sectors."
    elif pat == "random":
        return f"Evenly scattered stochastic distribution across cylinder space with wide spatial spread ({spread:.2f}) and balanced directional variance."
    else:
        return "Spatial request pattern evaluated on disk cylinder distribution metrics."


def recommend_rule_based_algorithm(
    requests: List[int],
    initial_head: int = 50,
    disk_size: int = 200,
    direction: str = "UP",
    arrival_pattern: str = "all_at_once",
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Analytical Rule-Based Adaptive Engine based on Operating System principles.
    Evaluates:
      - Spread, density, clustering, direction bias, queue length, arrival pattern,
        current head position, seek direction, and spatial concentration.
    Returns:
      - recommended_algorithm: FCFS, SSTF, SCAN, or C-SCAN
      - detected_pattern: workload pattern label
      - reason: detailed technical rationale
    """
    if not requests:
        return {
            "recommended_algorithm": "SSTF",
            "detected_pattern": "Empty Queue",
            "reason": "Queue is empty; defaulting to SSTF.",
            "confidence": 1.0
        }

    cls_info = classify_workload(requests, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
    features = cls_info["features"]
    pattern = cls_info["workload_type"]
    n = len(requests)
    spread = features["spread"]
    density = features["density"]
    clustering = features["clustering"]
    direction_bias = features["direction_bias"]
    details = features["details"]
    net_flow = details.get("net_flow", 0.0)
    arr_pat = (arrival_pattern or "all_at_once").lower()

    dir_norm = direction.upper()

    # Rule 1: Very short queues (N <= 3) -> FCFS minimizes overhead
    if n <= 3:
        return {
            "recommended_algorithm": "FCFS",
            "detected_pattern": f"{pattern.capitalize()} (Low Volume, N={n})",
            "reason": f"Queue length is very short (N={n}); FCFS eliminates scheduling and reordering overhead with negligible seek penalty.",
            "confidence": 0.88,
            "features": features
        }

    # Rule 2: Highly monotonic sequential streaming workload
    if pattern == "sequential" or (direction_bias > 0.70 and details["cv_diff"] < 0.6):
        # If head is behind the flow and direction matches
        flow_up = net_flow > 0
        head_aligned = (flow_up and dir_norm == "UP" and initial_head <= min(requests)) or \
                       (not flow_up and dir_norm == "DOWN" and initial_head >= max(requests))
        if head_aligned or arr_pat == "sequential":
            return {
                "recommended_algorithm": "FCFS",
                "detected_pattern": "Sequential Streaming Workload",
                "reason": f"Strong unidirectional monotonicity ({direction_bias:.2f}) aligned with arrival sequence; FCFS preserves natural contiguous physical cylinder flow.",
                "confidence": 0.85,
                "features": features
            }
        else:
            return {
                "recommended_algorithm": "SSTF",
                "detected_pattern": "Sequential Stride Workload",
                "reason": "Sequential requests with offset head; SSTF tracks adjacent contiguous cylinders greedily without unnecessary boundary sweeps.",
                "confidence": 0.82,
                "features": features
            }

    # Rule 3: Clustered hotspots
    if pattern == "clustered" or (clustering >= 0.45 and density >= 0.35):
        return {
            "recommended_algorithm": "SSTF",
            "detected_pattern": "Clustered Workload",
            "reason": f"Requests are heavily concentrated near spatial hotspots (clustering score {clustering:.2f}); SSTF rapidly services local clusters with minimal local seek distance.",
            "confidence": 0.90,
            "features": features
        }

    # Rule 4: Wide spread under heavy queue or continuous arrival -> C-SCAN for uniform fairness
    if spread >= 0.58 and (n >= 22 or arr_pat in ["continuous", "bursty"]):
        return {
            "recommended_algorithm": "C-SCAN",
            "detected_pattern": "Wide Spread Heavy Workload",
            "reason": f"High cylinder spread ({spread:.2f}) under heavy/continuous traffic; C-SCAN provides strictly uniform waiting time distribution and prevents starvation at outer cylinders.",
            "confidence": 0.86,
            "features": features
        }

    # Rule 5: Wide spread under moderate traffic -> SCAN elevator
    if spread >= 0.50 or pattern == "bursty":
        return {
            "recommended_algorithm": "SCAN",
            "detected_pattern": f"{pattern.capitalize()} Workload",
            "reason": f"Dispersed requests across disk tracks (spread {spread:.2f}); SCAN sweeps along the active seek direction ({dir_norm}) to eliminate starvation with predictable bounded service times.",
            "confidence": 0.84,
            "features": features
        }

    # Rule 6: Moderate localized spread -> SSTF
    return {
        "recommended_algorithm": "SSTF",
        "detected_pattern": "Localized Stochastic Workload",
        "reason": f"Moderate spread ({spread:.2f}) and localized track distances; SSTF optimizes instantaneous seek distance from current head (Cyl {initial_head}).",
        "confidence": 0.78,
        "features": features
    }


def predict_best_algorithm(
    requests: List[int],
    initial_head: int = 50,
    disk_size: int = 200,
    direction: str = "UP",
    arrival_pattern: str = "all_at_once",
    arrival_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Composite decision engine:
      - Evaluates simulation seek distances for all 4 algorithms
      - Computes analytical Rule-Based Recommendation
      - Selects optimal algorithm for Adaptive mode
    """
    if not requests:
        return {
            "predicted_algorithm": "SSTF",
            "best_algorithm": "SSTF",
            "reason": "Defaulting to SSTF for empty queue.",
            "simulated_distances": {"FCFS": 0, "SSTF": 0, "SCAN": 0, "C-SCAN": 0},
            "rule_based": {
                "recommended_algorithm": "SSTF",
                "reason": "Queue is empty; defaulting to SSTF."
            }
        }

    # Evaluate exact seek distances
    results = {
        "FCFS": fcfs(requests, initial_head, disk_size, direction)["total_seek_distance"],
        "SSTF": sstf(requests, initial_head, disk_size, direction)["total_seek_distance"],
        "SCAN": scan(requests, initial_head, disk_size, direction)["total_seek_distance"],
        "C-SCAN": c_scan(requests, initial_head, disk_size, direction)["total_seek_distance"],
    }

    sorted_algos = sorted(results.items(), key=lambda item: item[1])
    sim_best_algo, min_distance = sorted_algos[0]

    # Analytical rule-based recommendation
    rule_rec = recommend_rule_based_algorithm(
        requests=requests,
        initial_head=initial_head,
        disk_size=disk_size,
        direction=direction,
        arrival_pattern=arrival_pattern,
        arrival_times=arrival_times
    )

    classification = classify_workload(requests, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)

    return {
        "predicted_algorithm": sim_best_algo,
        "best_algorithm": sim_best_algo,
        "simulation_winner": sim_best_algo,
        "min_seek_distance": min_distance,
        "simulated_distances": results,
        "classification": classification,
        "rule_based": rule_rec,
        "reason": f"Simulation indicates {sim_best_algo} minimizes total seek distance ({min_distance} cyl). Analytical recommendation: {rule_rec['recommended_algorithm']} ({rule_rec['reason']})"
    }
