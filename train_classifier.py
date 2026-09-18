"""
train_classifier.py
Generates labeled synthetic disk request workloads, extracts features,
trains a scikit-learn Decision Tree Classifier to predict the optimal algorithm
using a dual-objective evaluation function (Seek Distance + Fairness/Starvation),
and exports the trained model, dataset, and visualizations.
"""

import os
import random
import csv
import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

from disk_scheduler.algorithms import fcfs, sstf, scan, c_scan
from disk_scheduler.workload_generator import generate_workload
from disk_scheduler.classifier import extract_features
from disk_scheduler.metrics import compute_metrics


def evaluate_dual_objective_winner(
    results_map: dict,
    metrics_map: dict,
    count: int,
    spread: float = 0.5
) -> str:
    """
    Evaluates optimal algorithm under documented Operating Systems dual-objective:
      Objective = w_seek * Normalized_Seek_Distance + w_fairness * Normalized_Fairness_Variance + Starvation_Penalty
    Balances seek distance minimization with bounded response times and starvation avoidance.
    """
    algos = ["FCFS", "SSTF", "SCAN", "C-SCAN"]

    seeks = {a: results_map[a]["total_seek_distance"] for a in algos}
    variances = {a: metrics_map[a]["fairness_variance"] for a in algos}
    max_resps = {a: metrics_map[a]["max_response_time_ms"] for a in algos}
    mean_resps = {a: metrics_map[a]["mean_response_time_ms"] for a in algos}

    min_seek = min(seeks.values())
    max_seek = max(seeks.values())
    seek_range = max(1.0, max_seek - min_seek)

    min_var = min(variances.values())
    max_var = max(variances.values())
    var_range = max(1.0, max_var - min_var)

    # For tiny queues, FCFS has virtually no overhead
    if count <= 4 and seeks["FCFS"] <= min_seek * 1.15:
        return "FCFS"

    # For wide spread and heavy load, C-SCAN's circular sweep eliminates turnaround asymmetry
    if spread >= 0.65 and count >= 20 and variances["C-SCAN"] <= min_var * 1.15:
        return "C-SCAN"

    scores = {}
    for a in algos:
        norm_seek = (seeks[a] - min_seek) / seek_range
        norm_var = (variances[a] - min_var) / var_range

        # Starvation penalty: if worst-case request response time is severe
        starvation_ratio = max_resps[a] / max(1.0, mean_resps[a])
        starvation_penalty = 0.25 if starvation_ratio > 2.8 else 0.0

        # Weighted objective: 50% seek distance, 50% fairness variance + starvation
        score = 0.50 * norm_seek + 0.50 * norm_var + starvation_penalty
        scores[a] = score

    return min(algos, key=lambda a: scores[a])


def generate_training_data(num_samples: int = 800, random_seed: int = 42):
    """
    Generates synthetic workloads evenly split across 4 pattern types and arrival patterns.
    Runs all 4 algorithms, computes seek distance and fairness metrics, labels with
    dual-objective optimal algorithm, and extracts the spatial features.
    """
    random.seed(random_seed)
    np.random.seed(random_seed)

    patterns = ["random", "sequential", "clustered", "bursty"]
    arrival_patterns = ["all_at_once", "sequential", "random", "bursty", "continuous"]
    samples_per_pattern = num_samples // len(patterns)

    rows = []
    print(f"Generating {num_samples} synthetic workloads ({samples_per_pattern} per spatial pattern)...")

    sample_id = 0
    for pat in patterns:
        for _ in range(samples_per_pattern):
            sample_id += 1
            count = random.randint(10, 50)
            disk_size = random.choice([150, 200, 250, 300, 400])
            initial_head = random.randint(0, disk_size - 1)
            direction = random.choice(["UP", "DOWN"])
            arr_pat = random.choice(arrival_patterns)
            sub_seed = random.randint(1, 100000)

            # Generate requests with arrival pattern
            wl_data = generate_workload(
                pattern=pat,
                count=count,
                disk_size=disk_size,
                seed=sub_seed,
                arrival_pattern=arr_pat
            )
            requests = wl_data["requests"]
            arrival_times = wl_data.get("arrival_times")

            # Run all 4 algorithms
            res_fcfs = fcfs(requests, initial_head, disk_size, direction)
            res_sstf = sstf(requests, initial_head, disk_size, direction)
            res_scan = scan(requests, initial_head, disk_size, direction)
            res_cscan = c_scan(requests, initial_head, disk_size, direction)

            results_map = {
                "FCFS": res_fcfs,
                "SSTF": res_sstf,
                "SCAN": res_scan,
                "C-SCAN": res_cscan
            }

            # Compute full performance & fairness metrics
            metrics_map = {
                a: compute_metrics(results_map[a], requests, initial_head, disk_size, arrival_times=arrival_times)
                for a in results_map
            }

            # Extract features
            feat = extract_features(requests, disk_size=disk_size, initial_head=initial_head, arrival_times=arrival_times)
            spread = feat["spread"]
            density = feat["density"]
            clustering = feat["clustering"]
            direction_bias = feat["direction_bias"]

            # Dual-objective target algorithm (Seek Distance + Fairness)
            best_algorithm = evaluate_dual_objective_winner(results_map, metrics_map, count, spread=spread)

            rows.append({
                "sample_id": sample_id,
                "pattern": pat,
                "arrival_pattern": arr_pat,
                "count": count,
                "disk_size": disk_size,
                "initial_head": initial_head,
                "direction": direction,
                "spread": spread,
                "density": density,
                "clustering": clustering,
                "direction_bias": direction_bias,
                "fcfs_dist": res_fcfs["total_seek_distance"],
                "sstf_dist": res_sstf["total_seek_distance"],
                "scan_dist": res_scan["total_seek_distance"],
                "cscan_dist": res_cscan["total_seek_distance"],
                "fcfs_var": metrics_map["FCFS"]["fairness_variance"],
                "sstf_var": metrics_map["SSTF"]["fairness_variance"],
                "scan_var": metrics_map["SCAN"]["fairness_variance"],
                "cscan_var": metrics_map["C-SCAN"]["fairness_variance"],
                "best_algorithm": best_algorithm
            })

    print(f"Generated {len(rows)} samples successfully.")
    return rows


def save_dataset_to_csv(rows, filename="workload_dataset.csv"):
    """Saves rows to CSV."""
    fieldnames = [
        "sample_id", "pattern", "arrival_pattern", "count", "disk_size", "initial_head", "direction",
        "spread", "density", "clustering", "direction_bias",
        "fcfs_dist", "sstf_dist", "scan_dist", "cscan_dist",
        "fcfs_var", "sstf_var", "scan_var", "cscan_var",
        "best_algorithm"
    ]
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Dataset exported to: {filename}")


def train_and_export_model(rows, model_save_path="classifier_model.pkl"):
    """
    Trains a DecisionTreeClassifier on [spread, density, clustering, direction_bias],
    evaluates on test set, serializes the model, and exports visualizations.
    """
    feature_names = ["spread", "density", "clustering", "direction_bias"]
    X = np.array([[r[f] for f in feature_names] for r in rows], dtype=float)
    y = np.array([r["best_algorithm"] for r in rows], dtype=str)

    unique_classes, counts = np.unique(y, return_counts=True)
    print("\nClass distribution in generated dataset:")
    for cls, cnt in zip(unique_classes, counts):
        print(f"  {cls}: {cnt} ({cnt/len(y)*100:.1f}%)")

    # 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"\nTraining on {len(X_train)} samples, testing on {len(X_test)} samples...")

    # DecisionTreeClassifier with balanced class weight and controlled depth
    clf = DecisionTreeClassifier(
        criterion="gini",
        max_depth=6,
        min_samples_split=6,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n==========================================")
    print(f"Decision Tree Test Accuracy: {acc * 100:.2f}%")
    print(f"==========================================")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Feature Importances
    print("Feature Importances:")
    for f_name, imp in zip(feature_names, clf.feature_importances_):
        print(f"  - {f_name:15s}: {imp:.4f}")

    # Save trained model to root and package directory
    joblib.dump(clf, model_save_path)
    print(f"\nTrained model saved to: {model_save_path}")

    pkg_model_path = os.path.join("disk_scheduler", os.path.basename(model_save_path))
    joblib.dump(clf, pkg_model_path)
    print(f"Trained model also copied to package: {pkg_model_path}")

    # Export text visualization of rules
    tree_text = export_text(clf, feature_names=feature_names)
    with open("tree_rules.txt", "w", encoding="utf-8") as f:
        f.write("=== DECISION TREE CLASSIFIER RULES ===\n")
        f.write(f"Target: Optimal Disk Scheduling Algorithm (FCFS, SSTF, SCAN, C-SCAN)\n")
        f.write(f"Objective: Dual-Objective (Seek Distance + Fairness Variance)\n")
        f.write(f"Test Accuracy: {acc * 100:.2f}%\n\n")
        f.write(tree_text)
    print("Text tree rules saved to: tree_rules.txt")

    # Export visual plot of decision tree
    plt.figure(figsize=(18, 9), dpi=150)
    plot_tree(
        clf,
        feature_names=feature_names,
        class_names=clf.classes_,
        filled=True,
        rounded=True,
        fontsize=9
    )
    plt.title(f"Disk Scheduling Optimal Algorithm Decision Tree (Accuracy: {acc * 100:.1f}%)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig("decision_tree_visualization.png", bbox_inches="tight")
    plt.close()
    print("Visual tree plot saved to: decision_tree_visualization.png")

    # Also copy to disk_scheduler folder if present
    if os.path.isdir("disk_scheduler"):
        try:
            with open(os.path.join("disk_scheduler", "tree_rules.txt"), "w", encoding="utf-8") as f:
                f.write(tree_text)
        except Exception:
            pass

    return clf, acc


if __name__ == "__main__":
    data_rows = generate_training_data(num_samples=800, random_seed=42)
    save_dataset_to_csv(data_rows, filename="workload_dataset.csv")
    train_and_export_model(data_rows, model_save_path="classifier_model.pkl")
