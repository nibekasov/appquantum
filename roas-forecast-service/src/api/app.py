from __future__ import annotations

from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.api.schemas import PredictRequest, PredictResponse
from src.core.ch import get_client
from src.core.features import select_inference_features
from src.core.modeling import load_model

app = FastAPI(title="ROAS Forecast API", version="0.1.0")


def _build_where(req: PredictRequest) -> tuple[str, dict]:
    clauses = ["date_idx >= %(df)s", "date_idx <= %(dt)s"]
    params = {"df": req.date_from, "dt": req.date_to}
    if req.opt_group_map:
        clauses.append("opt_group_map = %(opt)s")
        params["opt"] = req.opt_group_map
    if req.country_map:
        clauses.append("country_map = %(geo)s")
        params["geo"] = req.country_map
    if req.conv_window_map:
        clauses.append("conv_window_map = %(cw)s")
        params["cw"] = req.conv_window_map
    return " AND ".join(clauses), params


@lru_cache(maxsize=32)
def _get_model(level: str, target: str):
    return load_model(level=level, target=target)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    # Basic validation of required dims by level
    if req.level == "micro":
        # micro can accept partial filters (the aggregation will still work), but warn if none provided
        pass
    elif req.level == "mid":
        # mid ignores geo/cw in aggregation; filters are still allowed but will narrow raw rows
        pass

    where, params = _build_where(req)
    q = f"SELECT * FROM cohort_metrics WHERE {where}"

    client = get_client()
    try:
        res = client.query_df(q, parameters=params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ClickHouse query error: {e}")

    if res is None or len(res) == 0:
        raise HTTPException(status_code=404, detail="No rows found for given filters/date range")

    # Build inference matrix
    X, cat_cols = select_inference_features(res, level=req.level)

    # Load model
    try:
        bundle = _get_model(req.level, req.target)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Predict: return the cost-weighted average ROAS over the requested window.
    # If the request spans multiple dates/dim-slices, cost-weighting matches how ROAS aggregates.
    preds = pd.Series(bundle.model.predict(X)).clip(lower=0)
    if "cost" in X.columns and X["cost"].sum() > 0:
        w = X["cost"].astype(float)
        pred = float((preds * w).sum() / w.sum())
    else:
        pred = float(preds.mean())

    return PredictResponse(
        level=req.level,
        target=req.target,
        date_from=req.date_from,
        date_to=req.date_to,
        prediction=pred,
        rows=int(len(res)),
    )
