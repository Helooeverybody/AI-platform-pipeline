from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ExperimentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)


class ExecutionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: Literal["docker", "kubernetes"]
    runtime_image: str = Field(min_length=1)
    command: list[str] = Field(min_length=1)
    timeout_seconds: int = Field(gt=0)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment: ExperimentInfo
    execution: ExecutionConfig


def load_experiment(path: str | Path) -> ExperimentConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ExperimentConfig.model_validate(raw)
