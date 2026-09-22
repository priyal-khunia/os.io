"""
Flask Application for Disk Scheduling Simulator
Provides REST API endpoints for simulation, comparison, workload generation,
feature extraction, classification, multi-workload benchmarking, and arrival pattern evaluation.
"""

import os
from typing import List, Dict, Any, Optional
from flask import Flask, render_template, request, jsonify

from disk_scheduler.algorithms import (
    fcfs, sstf, scan, c_scan, run_algorithm, ALGORITHMS
)
from disk_scheduler.workload_generator import (
    generate_workload, generate_arrival_times, GENERATORS, ARRIVAL_PATTERNS
)
from disk_scheduler.classifier import (
    extract_features, classify_workload, predict_best_algorithm,
    recommend_rule_based_algorithm, generate_workload_description
)
from disk_scheduler.metrics import compute_metrics, compare_all_metrics
from disk_scheduler.ml_model import predict_ml_algorithm, load_ml_model

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

# Preload ML decision tree model at startup
load_ml_model()


def parse_request_payload(data: Dict[str, Any]) -> tuple:
    """Helper to parse and sanitize common request inputs, including arrival timing."""
    raw_requests = data.get("requests", [])
    if isinstance(raw_requests, str):
        # Support comma or space separated strings
        tokens = raw_requests.replace(",", " ").split()
        requests_list = [int(t) for t in tokens if t.lstrip("-").isdigit()]
    elif isinstance(raw_requests, list):
        requests_list = []
        for r in raw_requests:
            if isinstance(r, dict):
                cyl = r.get("cylinder")
                if cyl is not None:
                    requests_list.append(int(cyl))
            else:
                try:
                    requests_list.append(int(r))
                except (ValueError, TypeError):
                    pass
    else:
        requests_list = []

    disk_size = int(data.get("disk_size", 200))
    if disk_size <= 0:
        disk_size = 200

    # Single source of truth for initial_head
    raw_head = data.get("initial_head")
    if raw_head is not None and str(raw_head).strip() != "":
        try:
            initial_head = int(raw_head)
        except (ValueError, TypeError):
            initial_head = 0
    else:
        initial_head = 0

    direction = str(data.get("direction", "UP")).upper()
    if direction not in ["UP", "DOWN"]:
        direction = "UP"

    # Clamp cylinders to [0, disk_size - 1]
    clamped_requests = [max(0, min(disk_size - 1, r)) for r in requests_list]
    initial_head = max(0, min(disk_size - 1, initial_head))

    # Arrival pattern & arrival times
    arrival_pattern = str(data.get("arrival_pattern", "all_at_once")).lower().replace("-", "_").strip()
    raw_arrival_times = data.get("arrival_times")
    if isinstance(raw_arrival_times, list) and len(raw_arrival_times) == len(clamped_requests):
        try:
            arrival_times = [max(0.0, float(t)) for t in raw_arrival_times]
        except (ValueError, TypeError):
            arrival_times = generate_arrival_times(len(clamped_requests), arrival_pattern)
    else:
        arrival_times = generate_arrival_times(len(clamped_requests), arrival_pattern)

    return clamped_requests, initial_head, disk_size, direction, arrival_pattern, arrival_times


@app.route("/")
def index():
    """Renders main simulator dashboard."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "Adaptive Disk Scheduling Simulator API is running"})


@app.route("/api/generate-workload", methods=["POST"])
def api_generate_workload():
    """Generates workload requests with spatial distribution and arrival patterns."""
    try:
        data = request.get_json() or {}
        pattern = data.get("pattern", "random").lower()
        arrival_pattern = data.get("arrival_pattern", "all_at_once")
        count = int(data.get("count", 20))
        disk_size = int(data.get("disk_size", 200))
        seed = data.get("seed")
        seed = int(seed) if seed is not None and str(seed).strip() != "" else 0

        count = max(1, min(200, count))
        disk_size = max(10, min(10000, disk_size))

        result = generate_workload(
            pattern=pattern,
            count=count,
            disk_size=disk_size,
            seed=seed,
            arrival_pattern=arrival_pattern
        )
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/classify", methods=["POST"])
def api_classify():
    """Extracts features, classifies workload type, and evaluates both Rule-Based and ML prediction."""
    try:
        data = request.get_json() or {}
        requests_list, initial_head, disk_size, direction, arrival_pattern, arrival_times = parse_request_payload(data)

        classification = classify_workload(requests_list, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
        rule_rec = recommend_rule_based_algorithm(
            requests=requests_list,
            initial_head=initial_head,
            disk_size=disk_size,
            direction=direction,
            arrival_pattern=arrival_pattern,
            arrival_times=arrival_times
        )
        prediction = predict_best_algorithm(
            requests=requests_list,
            initial_head=initial_head,
            disk_size=disk_size,
            direction=direction,
            arrival_pattern=arrival_pattern,
            arrival_times=arrival_times
        )
        ml_prediction = predict_ml_algorithm(classification.get("features", {}))
        classification["ml_predicted_algorithm"] = ml_prediction["ml_predicted_algorithm"]
        classification["ml_prediction"] = ml_prediction

        return jsonify({
            "success": True,
            "data": {
                "classification": classification,
                "rule_based": rule_rec,
                "prediction": prediction,
                "ml_prediction": ml_prediction,
                "ml_predicted_algorithm": ml_prediction["ml_predicted_algorithm"]
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    Executes a chosen algorithm (or Adaptive Scheduler) and returns seek order,
    head movement sequence, and full performance telemetry metrics.
    """
    try:
        data = request.get_json() or {}
        requests_list, initial_head, disk_size, direction, arrival_pattern, arrival_times = parse_request_payload(data)
        algorithm_choice = str(data.get("algorithm", "FCFS")).upper().replace("_", "-")

        is_adaptive = (algorithm_choice == "ADAPTIVE")
        adaptive_info = None

        # Feature extraction & ML prediction
        classification = classify_workload(requests_list, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
        ml_prediction = predict_ml_algorithm(classification.get("features", {}))
        rule_rec = recommend_rule_based_algorithm(
            requests=requests_list,
            initial_head=initial_head,
            disk_size=disk_size,
            direction=direction,
            arrival_pattern=arrival_pattern,
            arrival_times=arrival_times
        )

        if is_adaptive:
            basis = str(data.get("adaptive_basis", "HYBRID")).upper()
            if basis == "ML" and ml_prediction.get("model_loaded", False):
                actual_algo = ml_prediction["ml_predicted_algorithm"]
                selection_basis = "ML Decision Tree"
                reason = f"ML Decision Tree predicted {actual_algo} with {int(ml_prediction['confidence']*100)}% confidence based on spatial features."
            elif basis == "RULE":
                actual_algo = rule_rec["recommended_algorithm"]
                selection_basis = "Rule-Based Expert Engine"
                reason = rule_rec["reason"]
            else:
                # Combined Hybrid Ensemble: Use ML if high confidence (>= 0.65), otherwise Rule-Based
                if ml_prediction.get("model_loaded", False) and ml_prediction.get("confidence", 0) >= 0.65:
                    actual_algo = ml_prediction["ml_predicted_algorithm"]
                    selection_basis = f"ML Decision Tree ({int(ml_prediction['confidence']*100)}% conf)"
                    reason = f"Decision tree classifier prioritized {actual_algo} for [spread: {classification['features']['spread']}, cluster: {classification['features']['clustering']}]."
                else:
                    actual_algo = rule_rec["recommended_algorithm"]
                    selection_basis = "Rule-Based Expert Engine"
                    reason = rule_rec["reason"]

            adaptive_info = {
                "selected_algorithm": actual_algo,
                "selection_basis": selection_basis,
                "reason": reason,
                "workload_type": classification["workload_type"],
                "rule_based_choice": rule_rec["recommended_algorithm"],
                "ml_choice": ml_prediction["ml_predicted_algorithm"]
            }
        else:
            actual_algo = algorithm_choice

        # Run the selected algorithm
        algo_result = run_algorithm(actual_algo, requests_list, initial_head, disk_size, direction)

        # Calculate all 5 metrics
        metrics = compute_metrics(
            algo_result,
            requests_list,
            initial_head,
            disk_size,
            arrival_times=arrival_times
        )

        classification["ml_predicted_algorithm"] = ml_prediction["ml_predicted_algorithm"]
        classification["ml_prediction"] = ml_prediction

        # Prepare request items for frontend visualization
        request_items = [
            {"id": f"R{i + 1}", "cylinder": requests_list[i], "arrival_time": arrival_times[i]}
            for i in range(len(requests_list))
        ]

        return jsonify({
            "success": True,
            "data": {
                "algorithm": actual_algo,
                "requested_algorithm": algorithm_choice,
                "is_adaptive": is_adaptive,
                "adaptive_info": adaptive_info,
                "seek_order": algo_result["seek_order"],
                "head_movement_sequence": algo_result["head_movement_sequence"],
                "total_seek_distance": algo_result["total_seek_distance"],
                "steps": algo_result["steps"],
                "metrics": metrics,
                "classification": classification,
                "rule_based": rule_rec,
                "ml_prediction": ml_prediction,
                "ml_predicted_algorithm": ml_prediction["ml_predicted_algorithm"],
                "request_items": request_items,
                "config": {
                    "initial_head": initial_head,
                    "disk_size": disk_size,
                    "direction": direction,
                    "arrival_pattern": arrival_pattern,
                    "requests_count": len(requests_list)
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """Runs all 4 classical algorithms PLUS Adaptive on the input workload and returns side-by-side metrics."""
    try:
        data = request.get_json() or {}
        requests_list, initial_head, disk_size, direction, arrival_pattern, arrival_times = parse_request_payload(data)

        # Classical 4 algorithms
        comparison = compare_all_metrics(requests_list, initial_head, disk_size, direction, arrival_times=arrival_times)
        classification = classify_workload(requests_list, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
        rule_rec = recommend_rule_based_algorithm(
            requests=requests_list,
            initial_head=initial_head,
            disk_size=disk_size,
            direction=direction,
            arrival_pattern=arrival_pattern,
            arrival_times=arrival_times
        )

        adaptive_algo = rule_rec["recommended_algorithm"]
        adaptive_result = comparison[adaptive_algo]["result"]
        adaptive_metrics = dict(comparison[adaptive_algo]["metrics"])
        comparison["Adaptive"] = {
            "result": adaptive_result,
            "metrics": adaptive_metrics,
            "selected_algorithm": adaptive_algo,
            "reason": rule_rec["reason"]
        }

        # Ranking based on seek distance (including Adaptive)
        ranking = sorted(
            [
                {
                    "algorithm": name,
                    "seek_distance": details["metrics"]["seek_distance"],
                    "service_time_ms": details["metrics"]["service_time_ms"],
                    "throughput_req_per_sec": details["metrics"]["throughput_req_per_sec"],
                    "fairness_variance": details["metrics"]["fairness_variance"],
                    "jains_fairness_index": details["metrics"].get("jains_fairness_index", 1.0),
                    "mean_response_time_ms": details["metrics"]["mean_response_time_ms"]
                }
                for name, details in comparison.items()
            ],
            key=lambda item: item["seek_distance"]
        )

        return jsonify({
            "success": True,
            "data": {
                "comparison": comparison,
                "ranking": ranking,
                "classification": classification,
                "adaptive_selection": adaptive_algo,
                "config": {
                    "initial_head": initial_head,
                    "disk_size": disk_size,
                    "direction": direction,
                    "arrival_pattern": arrival_pattern,
                    "requests_count": len(requests_list)
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/compare-all-workloads", methods=["POST"])
def api_compare_all_workloads():
    """
    Generates all 4 workload types (random, sequential, clustered, bursty)
    and benchmarks all 4 algorithms plus Adaptive on each pattern.
    """
    try:
        data = request.get_json() or {}
        count = int(data.get("count", 25))
        disk_size = int(data.get("disk_size", 200))
        initial_head = int(data.get("initial_head", 50))
        direction = str(data.get("direction", "UP")).upper()
        arrival_pattern = str(data.get("arrival_pattern", "all_at_once")).lower()
        seed = data.get("seed")
        seed = int(seed) if seed is not None and str(seed).strip() != "" else 0

        count = max(5, min(100, count))
        disk_size = max(20, min(2000, disk_size))
        initial_head = max(0, min(disk_size - 1, initial_head))

        patterns = ["random", "sequential", "clustered", "bursty"]
        results: Dict[str, Any] = {}

        for pat in patterns:
            wl = generate_workload(
                pattern=pat,
                count=count,
                disk_size=disk_size,
                seed=seed,
                arrival_pattern=arrival_pattern
            )
            reqs = wl["requests"]
            arr_times = wl["arrival_times"]

            comp = compare_all_metrics(reqs, initial_head, disk_size, direction, arrival_times=arr_times)
            cls_info = classify_workload(reqs, disk_size=disk_size, initial_head=initial_head, arrival_times=arr_times)
            rule_rec = recommend_rule_based_algorithm(
                requests=reqs,
                initial_head=initial_head,
                disk_size=disk_size,
                direction=direction,
                arrival_pattern=arrival_pattern,
                arrival_times=arr_times
            )

            # Include Adaptive
            adaptive_algo = rule_rec["recommended_algorithm"]
            comp["Adaptive"] = {
                "result": comp[adaptive_algo]["result"],
                "metrics": dict(comp[adaptive_algo]["metrics"]),
                "selected_algorithm": adaptive_algo,
                "reason": rule_rec["reason"]
            }

            best_classical = min(["FCFS", "SSTF", "SCAN", "C-SCAN"], key=lambda a: comp[a]["metrics"]["seek_distance"])
            pattern_desc = generate_workload_description(pat, cls_info.get("features"))
            cls_info["reason"] = pattern_desc

            results[pat] = {
                "requests": reqs,
                "arrival_times": arr_times,
                "description": pattern_desc,
                "classification": cls_info,
                "rule_based": rule_rec,
                "comparison": comp,
                "adaptive_choice": adaptive_algo,
                "winner": {
                    "algorithm": best_classical,
                    "seek_distance": comp[best_classical]["metrics"]["seek_distance"],
                    "service_time_ms": comp[best_classical]["metrics"]["service_time_ms"],
                    "fairness_variance": comp[best_classical]["metrics"]["fairness_variance"],
                    "jains_fairness_index": comp[best_classical]["metrics"].get("jains_fairness_index", 1.0)
                }
            }

        return jsonify({
            "success": True,
            "data": {
                "workload_benchmarks": results,
                "config": {
                    "count": count,
                    "disk_size": disk_size,
                    "initial_head": initial_head,
                    "direction": direction,
                    "arrival_pattern": arrival_pattern,
                    "seed": seed
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/compare-arrival-patterns", methods=["POST"])
def api_compare_arrival_patterns():
    """
    Evaluates how algorithms perform across different arrival patterns:
    all-at-once, sequential, random, bursty, continuous.
    Fulfills Phase 2 arrival pattern evaluation requirement.
    """
    try:
        data = request.get_json() or {}
        requests_list, initial_head, disk_size, direction, _, _ = parse_request_payload(data)
        if not requests_list:
            requests_list = [98, 183, 37, 122, 14, 124, 65, 67]

        patterns = ["all_at_once", "sequential", "random", "bursty", "continuous"]
        results: Dict[str, Any] = {}

        for arr_pat in patterns:
            arr_times = generate_arrival_times(len(requests_list), arrival_pattern=arr_pat, seed=42)
            comp = compare_all_metrics(requests_list, initial_head, disk_size, direction, arrival_times=arr_times)
            rule_rec = recommend_rule_based_algorithm(
                requests=requests_list,
                initial_head=initial_head,
                disk_size=disk_size,
                direction=direction,
                arrival_pattern=arr_pat,
                arrival_times=arr_times
            )

            adaptive_algo = rule_rec["recommended_algorithm"]
            comp["Adaptive"] = {
                "result": comp[adaptive_algo]["result"],
                "metrics": dict(comp[adaptive_algo]["metrics"]),
                "selected_algorithm": adaptive_algo
            }

            results[arr_pat] = {
                "arrival_pattern": arr_pat,
                "arrival_times": arr_times,
                "comparison": comp,
                "adaptive_choice": adaptive_algo,
                "summary": {
                    algo: {
                        "seek_distance": comp[algo]["metrics"]["seek_distance"],
                        "service_time_ms": comp[algo]["metrics"]["service_time_ms"],
                        "mean_response_time_ms": comp[algo]["metrics"]["mean_response_time_ms"],
                        "fairness_variance": comp[algo]["metrics"]["fairness_variance"],
                        "jains_fairness_index": comp[algo]["metrics"].get("jains_fairness_index", 1.0)
                    }
                    for algo in ["FCFS", "SSTF", "SCAN", "C-SCAN", "Adaptive"]
                }
            }

        return jsonify({
            "success": True,
            "data": {
                "arrival_benchmarks": results,
                "config": {
                    "requests_count": len(requests_list),
                    "disk_size": disk_size,
                    "initial_head": initial_head,
                    "direction": direction
                }
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
