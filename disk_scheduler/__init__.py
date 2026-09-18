"""
Disk Scheduler Package
"""

from disk_scheduler.algorithms import fcfs, sstf, scan, c_scan, run_algorithm, ALGORITHMS
from disk_scheduler.workload_generator import generate_workload, GENERATORS
from disk_scheduler.classifier import extract_features, classify_workload, predict_best_algorithm, generate_workload_description
from disk_scheduler.ml_model import predict_ml_algorithm, load_ml_model
from disk_scheduler.metrics import compute_metrics, compare_all_metrics

__all__ = [
    "fcfs",
    "sstf",
    "scan",
    "c_scan",
    "run_algorithm",
    "ALGORITHMS",
    "generate_workload",
    "GENERATORS",
    "extract_features",
    "classify_workload",
    "predict_best_algorithm",
    "generate_workload_description",
    "predict_ml_algorithm",
    "load_ml_model",
    "compute_metrics",
    "compare_all_metrics"
]
