import pytest
from pydantic import ValidationError

from mini_ml.config import ExperimentConfig, load_experiment


def test_hello_experiment_loads():
    config = load_experiment("configs/hello.yaml")

    assert config.experiment.name == "hello-mlops"
    assert config.execution.backend == "docker"
    assert config.execution.command


def test_empty_command_is_rejected():
    with pytest.raises(ValidationError):
        ExperimentConfig.model_validate(
            {
                "experiment": {"name": "invalid-job"},
                "execution": {
                    "backend": "docker",
                    "runtime_image": "python:3.12-slim",
                    "command": [],
                    "timeout_seconds": 60,
                },
            }
        )
