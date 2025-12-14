CREATE DATABASE IF NOT EXISTS roas;

CREATE TABLE IF NOT EXISTS roas.cohort_metrics (
    country_map String,
    conv_window_map String,
    opt_group_map String,
    date_map String,
    date_idx UInt32,

    installs UInt32,
    cpi Float64,
    cost Float64,

    payers_d0 UInt32,
    payers_d1 UInt32,
    payers_d3 UInt32,
    payers_d7 UInt32,
    payers_d14 UInt32,
    payers_d30 UInt32,
    payers_d60 UInt32,
    payers_d90 UInt32,

    iaa_roas_d0 Float32,
    iaa_roas_d1 Float32,
    iaa_roas_d3 Float32,
    iaa_roas_d7 Float32,
    iaa_roas_d14 Float32,
    iaa_roas_d30 Float32,
    iaa_roas_d60 Float32,
    iaa_roas_d90 Float32,

    iap_roas_d0 Float32,
    iap_roas_d1 Float32,
    iap_roas_d3 Float32,
    iap_roas_d7 Float32,
    iap_roas_d14 Float32,
    iap_roas_d30 Float32,
    iap_roas_d60 Float32,
    iap_roas_d90 Float32,

    rv_acpu_d0 Float32,
    rv_acpu_d1 Float32,
    rv_acpu_d3 Float32,
    rv_acpu_d7 Float32,
    rv_acpu_d14 Float32,
    rv_acpu_d30 Float32,
    rv_acpu_d60 Float32,
    rv_acpu_d90 Float32
)
ENGINE = MergeTree
ORDER BY (date_idx, opt_group_map, country_map, conv_window_map);
