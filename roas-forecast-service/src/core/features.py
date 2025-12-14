from __future__ import annotations

import pandas as pd
import numpy as np

# Contract: features available at inference
DAYS = [0, 1, 3, 7]

CAT_COLS = ["country_map", "conv_window_map", "opt_group_map"]
BASE_NUM_COLS = [
    "date_idx",
    "installs",
    "cpi",
    "cost",
] + [
    f"payers_d{d}" for d in DAYS
] + [
    f"iaa_roas_d{d}" for d in DAYS
] + [
    f"iap_roas_d{d}" for d in DAYS
] + [
    f"rv_acpu_d{d}" for d in DAYS
]

DERIVED_COLS = [
    "payer_rate_d7",
    "iaa_growth_0_7",
    "iap_growth_0_7",
    "rv_growth_0_7",
    "log_installs",
    "log_cost",
]


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    installs = out["installs"].replace(0, np.nan)
    out["payer_rate_d7"] = (out["payers_d7"] / installs).fillna(0.0)

    out["iaa_growth_0_7"] = (out["iaa_roas_d7"] + 1e-6) / (out["iaa_roas_d0"] + 1e-6)
    out["iap_growth_0_7"] = (out["iap_roas_d7"] + 1e-6) / (out["iap_roas_d0"] + 1e-6)
    out["rv_growth_0_7"] = (out["rv_acpu_d7"] + 1e-6) / (out["rv_acpu_d0"] + 1e-6)

    out["log_installs"] = np.log1p(out["installs"])
    out["log_cost"] = np.log1p(out["cost"])
    return out


def aggregate_to_level(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Aggregate raw cohort rows to micro/mid/macro.

    The aggregation is revenue-weighted for ROAS columns:
      ROAS = sum(ROAS_i * cost_i) / sum(cost_i)
    And views-weighted for rv_acpu:
      rv_acpu = sum(rv_acpu_i * installs_i) / sum(installs_i)
    """
    if level not in {"micro", "mid", "macro"}:
        raise ValueError(f"Unsupported level: {level}")

    if level == "micro":
        keys = ["opt_group_map", "conv_window_map", "country_map", "date_idx"]
    elif level == "mid":
        keys = ["opt_group_map", "date_idx"]
    else:
        keys = ["date_idx"]

    d = df.copy()

    # Reconstruct revenues from ROAS and cost to aggregate correctly
    roas_cols = [c for c in d.columns if c.startswith("iaa_roas_d") or c.startswith("iap_roas_d")]
    rv_cols = [c for c in d.columns if c.startswith("rv_acpu_d")]

    for c in roas_cols:
        d[c + "_rev"] = d[c] * d["cost"]
    for c in rv_cols:
        d[c + "_views"] = d[c] * d["installs"]

    agg = {
        "installs": "sum",
        "cost": "sum",
        "cpi": "mean",  # in this task CPI is determined by opt_group; mean is safe
    }
    for c in [col for col in d.columns if col.startswith("payers_d")]:
        agg[c] = "sum"
    for c in roas_cols:
        agg[c + "_rev"] = "sum"
    for c in rv_cols:
        agg[c + "_views"] = "sum"

    out = d.groupby(keys, dropna=False).agg(agg).reset_index()

    for c in roas_cols:
        out[c] = out[c + "_rev"] / out["cost"].replace(0, np.nan)
    for c in rv_cols:
        out[c] = out[c + "_views"] / out["installs"].replace(0, np.nan)

    drop_cols = [c for c in out.columns if c.endswith("_rev") or c.endswith("_views")]
    out = out.drop(columns=drop_cols)

    return out


def select_inference_features(df: pd.DataFrame, level: str) -> tuple[pd.DataFrame, list[str]]:
    """Return (X, cat_cols_for_catboost) for inference."""
    base = aggregate_to_level(df, level)
    base = add_derived_features(base)

    # Determine cat columns present for this level
    if level == "macro":
        cat = []
    elif level == "mid":
        cat = ["opt_group_map"]
    else:
        cat = ["country_map", "conv_window_map", "opt_group_map"]

    cols = []
    cols += cat
    cols += [c for c in BASE_NUM_COLS if c in base.columns]
    cols += [c for c in DERIVED_COLS if c in base.columns]

    X = base[cols].copy()
    return X, cat
