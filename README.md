# AI-platform-pipeline

A learning project for running reproducible ML experiments with a small MLOps control plane. All sample data is synthetic.

## Current scope

The project currently validates an experiment YAML manifest. The sample manifest describes a simple Docker job; job launching and tracking will be added in later steps.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -c 'from mini_ml.config import load_experiment; print(load_experiment("configs/hello.yaml"))'
```

See `mini_research_mlops_project_spec.md` for the full project roadmap.
