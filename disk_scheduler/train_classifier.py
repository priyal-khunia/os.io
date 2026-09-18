"""
train_classifier.py (package copy)
Generates labeled synthetic disk request workloads, extracts features,
trains a scikit-learn Decision Tree Classifier to predict the optimal algorithm
using a dual-objective evaluation function (Seek Distance + Fairness/Starvation),
and exports the trained model, dataset, and visualizations.
"""

from train_classifier import (
    evaluate_dual_objective_winner,
    generate_training_data,
    save_dataset_to_csv,
    train_and_export_model
)

if __name__ == "__main__":
    data_rows = generate_training_data(num_samples=800, random_seed=42)
    save_dataset_to_csv(data_rows, filename="workload_dataset.csv")
    train_and_export_model(data_rows, model_save_path="classifier_model.pkl")
