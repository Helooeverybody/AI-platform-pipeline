# AI-platform-pipeline

A learning project for running reproducible ML experiments with a small MLOps control plane. All sample data is synthetic.

## Current scope

The project validates experiment YAML manifests and runs a small synthetic CPU training job on the host or in Docker. Job orchestration and experiment tracking will be added in later steps.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -c 'from mini_ml.config import load_experiment; print(load_experiment("configs/hello.yaml"))'
```

See `mini_research_mlops_project_spec.md` for the full project roadmap.

## CPU classifier workload

This synthetic workload is a small, real training job for exercising MLOps flows. It needs no external dataset. Install its extra dependencies and run it on the host:

```bash
python -m pip install -e ".[dev,ml]"
python examples/cpu_classifier/train.py --seed 42 --output-dir outputs/cpu_classifier
python examples/cpu_classifier/predict.py --model outputs/cpu_classifier/model.json --features 0 0 0 0 0 0 0 0
```

Training writes `metrics.json` and `model.json` under `outputs/cpu_classifier/`. The metrics include validation accuracy, dataset parameters, seed, sample counts and scikit-learn version. The model artifact is JSON with numeric weights for this binary logistic regression; prediction reads it without loading executable pickle data. The `outputs/` directory is ignored by Git.

The same job runs in Docker, with a bind mount to keep artifacts after the container exits:

```bash
docker build --build-arg "GIT_SHA=$(git rev-parse HEAD)" -t mini-ml-runtime:dev .
mkdir -p outputs/cpu_classifier
docker run --rm --user "$(id -u):$(id -g)" \
  --volume "$PWD/outputs/cpu_classifier:/outputs" \
  mini-ml-runtime:dev \
  python examples/cpu_classifier/train.py --seed 42 --output-dir /outputs
```

`configs/cpu_train.yaml` describes this Docker job using the project's existing experiment schema. It is a manifest for the future runner; Docker itself does not read the YAML file.
