"""Train a small, reproducible CPU classifier on synthetic data."""

import argparse
import json
from pathlib import Path

import numpy as np
import sklearn
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

DATASET = {
    "n_samples": 300,
    "n_features": 8,
    "n_informative": 5,
    "n_redundant": 1,
    "n_classes": 2,
    "flip_y": 0.01,
}


def make_dataset(seed: int) -> tuple[np.ndarray, np.ndarray]:
    return make_classification(**DATASET, random_state=seed)


def split_indices(labels: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(len(labels))
    return train_test_split(indices, test_size=0.2, stratify=labels, random_state=seed)


def train(seed: int, output_dir: Path) -> dict:
    features, labels = make_dataset(seed)
    train_indices, validation_indices = split_indices(labels, seed)

    classifier = LogisticRegression(max_iter=500)
    classifier.fit(features[train_indices], labels[train_indices])
    predictions = classifier.predict(features[validation_indices])

    metrics = {
        "validation_accuracy": float(
            accuracy_score(labels[validation_indices], predictions)
        ),
        "train_samples": len(train_indices),
        "validation_samples": len(validation_indices),
        "seed": seed,
        "dataset": DATASET,
        "scikit_learn_version": sklearn.__version__,
    }
    model = {
        "format_version": 1,
        "model_type": "binary_logistic_regression",
        "classes": classifier.classes_.astype(int).tolist(),
        "coefficients": classifier.coef_[0].tolist(),
        "intercept": float(classifier.intercept_[0]),
        "n_features": int(classifier.n_features_in_),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "model.json").write_text(
        json.dumps(model, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    metrics = train(args.seed, args.output_dir)
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
