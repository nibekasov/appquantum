from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from catboost import CatBoostRegressor

from .config import MODEL_DIR

Level = Literal["micro", "mid", "macro"]
Target = Literal["iap", "iaa"]


def _model_path(level: Level, target: Target) -> str:
    # Convention: models/<level>_<target>_latest.cbm
    fn = f"{level}_{target}_latest.cbm"
    return os.path.join(MODEL_DIR, fn)


@dataclass
class ModelBundle:
    level: Level
    target: Target
    model: CatBoostRegressor


def load_model(level: Level, target: Target) -> ModelBundle:
    path = _model_path(level, target)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Model artifact not found: {path}. Train first (src/training/train.py)"
        )
    m = CatBoostRegressor()
    m.load_model(path)
    return ModelBundle(level=level, target=target, model=m)
