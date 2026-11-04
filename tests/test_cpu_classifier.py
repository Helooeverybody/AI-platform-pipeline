import json

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from examples.cpu_classifier.predict import predict
from examples.cpu_classifier.train import make_dataset, split_indices, train


def test_dataset_and_split_reproducible_without_overlap():
    features, labels = make_dataset(42)
    repeated_features, repeated_labels = make_dataset(42)
    train_indices, validation_indices = split_indices(labels, 42)

    np.testing.assert_array_equal(features, repeated_features)
    np.testing.assert_array_equal(labels, repeated_labels)
    assert len(train_indices) == 240
    assert len(validation_indices) == 60
    assert set(train_indices).isdisjoint(validation_indices)
    assert len(set(train_indices) | set(validation_indices)) == 300
    assert np.array_equal(train_indices, split_indices(labels, 42)[0])


def test_model_artifact_matches_fitted_classifier(tmp_path):
    metrics = train(seed=42, output_dir=tmp_path)
    saved_metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    model = json.loads((tmp_path / "model.json").read_text(encoding="utf-8"))

    assert metrics == saved_metrics
    assert 0.0 <= metrics["validation_accuracy"] <= 1.0
    assert metrics["train_samples"] + metrics["validation_samples"] == 300
    assert model["n_features"] == len(model["coefficients"]) == 8

    features, labels = make_dataset(42)
    train_indices, validation_indices = split_indices(labels, 42)
    reference = LogisticRegression(max_iter=500).fit(
        features[train_indices], labels[train_indices]
    )
    for row in features[validation_indices]:
        assert predict(tmp_path / "model.json", row.tolist()) == int(
            reference.predict(row.reshape(1, -1))[0]
        )

    with pytest.raises(ValueError, match="Expected 8 features"):
        predict(tmp_path / "model.json", [0.0])
