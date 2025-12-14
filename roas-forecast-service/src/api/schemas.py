from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["micro", "mid", "macro"]
Target = Literal["iap", "iaa"]


class PredictRequest(BaseModel):
    level: Level = Field(..., description="Aggregation level: micro|mid|macro")
    target: Target = Field(..., description="Which ROAS to predict: iap|iaa")
    date_from: int = Field(..., description="Inclusive date_idx start")
    date_to: int = Field(..., description="Inclusive date_idx end")
    country_map: Optional[str] = None
    conv_window_map: Optional[str] = None
    opt_group_map: Optional[str] = None


class PredictResponse(BaseModel):
    level: Level
    target: Target
    date_from: int
    date_to: int
    prediction: float
    rows: int
