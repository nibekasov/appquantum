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
    dates = sorted(df["date_idx"].dropna().unique())
    if len(dates) == 0:
        raise ValueError("No date_idx values after filtering; dataset is empty.")
    if len(dates) == 1:
        # fallback: нет временной оси, всё в train
        cut = dates[0]
        tr = df.copy()
        te = df.iloc[0:0].copy()
        return tr, te, int(cut)

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

def _make_train_matrix(df: pd.DataFrame, level: str, tgt_col: str):
    base = aggregate_to_level(df, level)
    base = add_derived_features(base)

    # cat columns by level
    if level == "macro":
        cat_cols = []
    elif level == "mid":
        cat_cols = ["opt_group_map"]
    else:
        cat_cols = ["country_map", "conv_window_map", "opt_group_map"]

    feature_cols = []
    feature_cols += cat_cols
    feature_cols += [c for c in BASE_NUM_COLS if c in base.columns]
    feature_cols += [c for c in DERIVED_COLS if c in base.columns]

    # X / y / w из ОДНОЙ таблицы base
    X = base[feature_cols].copy()
    y = base[tgt_col].astype(float).copy()
    w = base["cost"].astype(float).copy() if "cost" in base.columns else None

    # фильтр уже после агрегации
    if w is not None:
        mask = w > 0
        X, y, w = X.loc[mask], y.loc[mask], w.loc[mask]

    return X, y, w, cat_cols


def _train_one(df_tr: pd.DataFrame, level: str, target: str) -> CatBoostRegressor:
    # 1) Приводим target к числу и фильтруем df_tr ОДИН РАЗ
    y_num = pd.to_numeric(df_tr[target], errors="coerce")
    df_tr = df_tr[np.isfinite(y_num)].copy()
    if len(df_tr) == 0:
        raise RuntimeError(f"No finite target values for {target} after filtering.")

    # 2) Фильтруем по весам тоже на df_tr, до сборки X/y/w
    if "cost" in df_tr.columns:
        df_tr["cost"] = pd.to_numeric(df_tr["cost"], errors="coerce").fillna(0.0)
        df_tr = df_tr[df_tr["cost"] > 0].copy()

    if len(df_tr) == 0:
        raise RuntimeError("No rows with cost > 0 after filtering; cannot train model.")

    # 3) Собираем фичи из УЖЕ отфильтрованного df_tr
    cat_cols, num_cols = _feature_cols(level)
    cols = [c for c in (cat_cols + num_cols) if c in df_tr.columns]

    X = df_tr[cols].copy()
    y = pd.to_numeric(df_tr[target], errors="coerce").astype(float)
    w = df_tr["cost"].astype(float) if "cost" in df_tr.columns else None

    # 4) Обучаем
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
    df = client.query_df("SELECT * FROM roas.cohort_metrics")  # лучше явно

    if df is None or len(df) == 0:
        raise RuntimeError("cohort_metrics is empty. Load data first.")



    for level in ["micro", "mid", "macro"]:
        df_lvl = aggregate_to_level(df, level)
        df_lvl = add_derived_features(df_lvl)

        for tgt, tgt_col in TARGETS.items():
            y = pd.to_numeric(df_lvl[tgt_col], errors="coerce")
            df_t = df_lvl[np.isfinite(y)].copy()

            print(
                f"[{level}/{tgt}] rows={len(df_t)}, "
                f"cost>0={(df_t['cost'] > 0).sum()}"
            )


            if len(df_t) == 0:
                print(f"[{level}/{tgt}] skip: no rows with non-null target {tgt_col}")
                continue

            tr, te, cut = _time_split(df_t, test_frac=0.2)
            print(f"[{level}/{tgt}] split cut_date_idx={cut}, train={len(tr)}, test={len(te)}")

            model = _train_one(tr, level, tgt_col)
            out_path = os.path.join(MODEL_DIR, f"{level}_{tgt}_latest.cbm")
            model.save_model(out_path)
            print(f"  saved {out_path}")


if __name__ == "__main__":
    main()
