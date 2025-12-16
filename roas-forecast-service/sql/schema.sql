CREATE DATABASE IF NOT EXISTS roas;

CREATE TABLE IF NOT EXISTS roas.cohort_metrics_raw
(
    country_map String,
    conv_window_map String,
    opt_group_map String,
    date_map String,

    installs UInt32,

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
ORDER BY (opt_group_map, country_map, conv_window_map, date_map);


CREATE OR REPLACE VIEW roas.cohort_metrics AS
SELECT
    country_map,
    conv_window_map,
    opt_group_map,
    date_map,

    -- date_idx: зависит от формата date_map
    -- если date_map вида 'YYYY-MM-DD'
    toUInt32(replaceOne(date_map, 'date_', '')) AS date_idx,


    installs,

    -- CPI по правилу из условия
    multiIf(
        opt_group_map = 'opt_group_1', 10.0,
        opt_group_map = 'opt_group_3', 40.0,
        opt_group_map IN ('opt_group_2','opt_group_4','opt_group_5'), 1.0,
        1.0
    ) AS cpi,

    installs * cpi AS cost,

    payers_d0, payers_d1, payers_d3, payers_d7, payers_d14, payers_d30, payers_d60, payers_d90,

    iaa_roas_d0, iaa_roas_d1, iaa_roas_d3, iaa_roas_d7, iaa_roas_d14, iaa_roas_d30, iaa_roas_d60, iaa_roas_d90,
    iap_roas_d0, iap_roas_d1, iap_roas_d3, iap_roas_d7, iap_roas_d14, iap_roas_d30, iap_roas_d60, iap_roas_d90,
    rv_acpu_d0, rv_acpu_d1, rv_acpu_d3, rv_acpu_d7, rv_acpu_d14, rv_acpu_d30, rv_acpu_d60, rv_acpu_d90
FROM roas.cohort_metrics_raw;
