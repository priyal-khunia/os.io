"""
ml_model.py
Module for loading and running inference with the scikit-learn Decision Tree Classifier.
Predicts optimal disk scheduling algorithm (FCFS, SSTF, SCAN, C-SCAN) from queue features.
"""

import os
from typing import Dict, Any, Optional, List
import numpy as np

# Global cached model
_MODEL = None
_MODEL_CLASSES = None


def get_model_paths() -> List[str]:
    """Returns candidate filepaths for the serialized model."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.abspath(os.path.join(current_dir, ".."))
    return [
        os.path.join(current_dir, "classifier_model.pkl"),
        os.path.join(workspace_dir, "classifier_model.pkl"),
        "classifier_model.pkl"
    ]


def load_ml_model(force_reload: bool = False):
    """
    Loads the trained DecisionTreeClassifier from disk using joblib.
    Caches the model instance for subsequent inferences.
    """
    global _MODEL, _MODEL_CLASSES
    if _MODEL is not None and not force_reload:
        return _MODEL

    import joblib

    for path in get_model_paths():
        if os.path.isfile(path):
            try:
                _MODEL = joblib.load(path)
                _MODEL_CLASSES = list(_MODEL.classes_)
                print(f"[ML Model] Loaded trained decision tree from: {path}")
                return _MODEL
            except Exception as e:
                print(f"[ML Model] Warning: Failed loading model from {path}: {e}")

    print("[ML Model] Notice: classifier_model.pkl not yet found. Model inference will use fallback.")
    return None


def predict_ml_algorithm(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predicts the optimal disk scheduling algorithm using the trained Decision Tree.

    Args:
        features: dictionary containing 'spread', 'density', 'clustering', 'direction_bias'.

    Returns:
        dict containing:
            ml_predicted_algorithm (str)
            confidence (float)
            probabilities (dict)
            model_loaded (bool)
            features_used (list)
    """
    model = load_ml_model()

    spread = float(features.get("spread", 0.5))
    density = float(features.get("density", 0.5))
    clustering = float(features.get("clustering", 0.5))
    direction_bias = float(features.get("direction_bias", 0.5))

    feat_vector = np.array([[spread, density, clustering, direction_bias]], dtype=float)

    if model is not None:
        try:
            pred_algo = str(model.predict(feat_vector)[0])
            probs = model.predict_proba(feat_vector)[0]
            classes = list(model.classes_)
            
            prob_dict = {str(cls): round(float(p), 4) for cls, p in zip(classes, probs)}
            best_idx = int(np.argmax(probs))
            confidence = float(probs[best_idx])

            return {
                "ml_predicted_algorithm": pred_algo,
                "confidence": round(confidence, 3),
                "probabilities": prob_dict,
                "model_loaded": True,
                "features_used": {
                    "spread": spread,
                    "density": density,
                    "clustering": clustering,
                    "direction_bias": direction_bias
                }
            }
        except Exception as e:
            print(f"[ML Model] Prediction error: {e}")

    # Fallback if model is not loaded or raises exception
    # Basic heuristic baseline
    fallback_algo = "SSTF" if clustering > 0.4 else "SCAN"
    return {
        "ml_predicted_algorithm": fallback_algo,
        "confidence": 0.70,
        "probabilities": {"SSTF": 0.45, "SCAN": 0.35, "C-SCAN": 0.15, "FCFS": 0.05},
        "model_loaded": False,
        "features_used": {
            "spread": spread,
            "density": density,
            "clustering": clustering,
            "direction_bias": direction_bias
        }
    }
