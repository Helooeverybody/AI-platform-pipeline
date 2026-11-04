"""Predict with the portable JSON artifact from the CPU classifier trainer."""

import argparse
import json
from pathlib import Path


def predict(model_path: Path, features: list[float]) -> int:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    if (
        model.get("format_version") != 1
        or model.get("model_type") != "binary_logistic_regression"
    ):
        raise ValueError("Unsupported model artifact")
    if len(features) != model["n_features"]:
        raise ValueError(
            f"Expected {model['n_features']} features, got {len(features)}"
        )

    score = sum(
        weight * feature
        for weight, feature in zip(model["coefficients"], features, strict=True)
    )
    score += model["intercept"]
    return int(model["classes"][int(score >= 0)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--features", type=float, nargs="+", required=True)
    args = parser.parse_args()

    print(json.dumps({"prediction": predict(args.model, args.features)}))


if __name__ == "__main__":
    main()
