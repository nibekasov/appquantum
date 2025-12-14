from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

from src.core.ch import get_client
from src.core.features import aggregate_to_level, add_derived_features

LEVELS = {
    "micro": ["opt_group_map", "conv_window_map", "country_map", "date_idx"],
    "mid": ["opt_group_map", "date_idx"],
    "macro": ["date_idx"],
}

TARGETS = {
    "iap": "iap_roas_d90",
    "iaa": "iaa_roas_d90",
}

MODEL_DIR = os.getenv("MODEL_DIR", "models")


def _time_split(df: pd.DataFrame, test_frac: float = 0.2):
    dates = sorted(df["date_idx"].unique())
    cut = dates[int(len(dates) * (1 - test_frac))]
    tr = df[df["date_idx"] < cut].copy()
    te = df[df["date_idx"] >= cut].copy()
    return tr, te, int(cut)


def _feature_cols(level: str) -> tuple[list[str], list[str]]:
    # cat cols per level
    if level == "macro":
        cat = []
    elif level == "mid":
        cat = ["opt_group_map"]
    else:
        cat = ["country_map", "conv_window_map", "opt_group_map"]

    # numeric features available at inference
    num = [
        "date_idx", "installs", "cpi", "cost",
        "payers_d0", "payers_d1", "payers_d3", "payers_d7",
        "iaa_roas_d0", "iaa_roas_d1", "iaa_roas_d3", "iaa_roas_d7",
        "iap_roas_d0", "iap_roas_d1", "iap_roas_d3", "iap_roas_d7",
        "rv_acpu_d0", "rv_acpu_d1", "rv_acpu_d3", "rv_acpu_d7",
        "payer_rate_d7", "iaa_growth_0_7", "iap_growth_0_7", "rv_growth_0_7",
        "log_installs", "log_cost",
    ]
    return cat, num


def _train_one(df_tr: pd.DataFrame, level: str, target: str) -> CatBoostRegressor:
    cat_cols, num_cols = _feature_cols(level)
    cols = cat_cols + num_cols

    X = df_tr[cols]
    y = df_tr[target]
    w = df_tr["cost"].astype(float)

    model = CatBoostRegressor(
        iterations=int(os.getenv("CB_ITER", "1500")),
        learning_rate=float(os.getenv("CB_LR", "0.03")),
        depth=int(os.getenv("CB_DEPTH", "8")),
        loss_function="MAE",
        random_seed=42,
        verbose=False,
    )

    model.fit(X, y, cat_features=cat_cols, sample_weight=w)
    return model


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    client = get_client()
    df = client.query_df("SELECT * FROM cohort_metrics")

    if df is None or len(df) == 0:
        raise RuntimeError("cohort_metrics is empty. Load data first (scripts/load_csv_to_clickhouse.py)")

    # Train per level and target
    for level in ["micro", "mid", "macro"]:
        df_lvl = aggregate_to_level(df, level)
        df_lvl = add_derived_features(df_lvl)

        # Drop rows without targets
        df_lvl = df_lvl.dropna(subset=["iaa_roas_d90", "iap_roas_d90"]).copy()

        tr, te, cut = _time_split(df_lvl, test_frac=0.2)
        print(f"[{level}] split cut_date_idx={cut}, train={len(tr)}, test={len(te)}")

        for tgt, tgt_col in TARGETS.items():
            model = _train_one(tr, level, tgt_col)
            out_path = os.path.join(MODEL_DIR, f"{level}_{tgt}_latest.cbm")
            model.save_model(out_path)
            print(f"  saved {out_path}")


if __name__ == "__main__":
    main()
