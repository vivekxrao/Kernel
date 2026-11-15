# KERNEL methodology and interpretation

## Data flow

1. Select an area of interest and temporal windows.
2. Query `COPERNICUS/S1_GRD_FLOAT` in Earth Engine, restricted to IW mode and scenes containing VH polarization.
3. Apply the installed PWTT package's Lee filter; select VV/VH; log-transform backscatter.
4. The package groups scenes by `relativeOrbitNumber_start`, runs the t-test for each orbit and combines orbit/polarization outputs.
5. The package creates the `T_statistic`, `damage`, `p_value`, `n_pre` and `n_post` bands.
6. Export/download the T-statistic raster.
7. Reproject building polygons to the raster CRS and compute zonal mean, maximum and valid-pixel count.
8. Apply the project's configurable building screening threshold to the mean T-statistic.
9. Serve scored GeoJSON and summary statistics to the dashboard; retain the raw scores for inspection.

## Temporal windows in the bundled Bakhmut configuration

- Cutoff / war start: 2022-02-22.
- Pre-event reference: 12 months before cutoff, 2021-02-22 through 2022-02-22.
- Inference start: 2024-07-01.
- Post interval: 1 month, through 2024-08-01.

These dates are the existing KERNEL working configuration. The inference period is a historical follow-up window, not the immediate post-event month.

## Package implementation facts from the installed source

The user's installed `pwtt.detect_damage` function accepts `aoi`, `inference_start`, `war_start`, `pre_interval`, `post_interval`, `footprints`, `viz`, `export`, `export_dir`, `export_name`, `export_scale`, `grid_scale` and `export_grid`. It does **not** accept a `threshold` argument.

The function filters Sentinel-1 GRD FLOAT for VH and IW, groups by relative orbit, runs the package's Lee filter, selects VV/VH and applies a natural logarithm. It computes absolute changes using a pooled two-sample standard error, computes p-values, applies spatial smoothing and returns the bands listed above.

In the installed code, `damage` is created with `t_smooth.gt(3)`. The building-level workflow in this bundle separately computes the mean of `T_statistic` inside each building footprint and sets a project screening flag when the mean exceeds the configured `DEFAULT_THRESHOLD` (default 3.3). These are two different operations.

## Before/after view

The two imagery tiles are median composites from the pre-event and inference windows, respectively, after the same broad Sentinel-1 IW/VV/VH selection and Lee/log preparation. They are aligned to the same AOI and Leaflet map. The T-statistic layer is produced by the PWTT package for the configured windows.

The context composites are not a claim that the t-test was computed from one single before image and one single after image. PWTT is a time-series statistical method and performs per-relative-orbit testing.

## Interpretation

- A larger T-statistic means a larger standardized difference in radar backscatter between the two temporal samples.
- A high score does not prove a building was destroyed. Radar changes may have other causes.
- Building-level means can be affected by footprint quality, pixel overlap and spatial spillover.
- `valid_pixels = 0` or a missing mean is `No raster data`, not a negative damage prediction.
- Every flagged building remains a candidate for qualified analyst review.

## Validation requirements

For any accuracy claim, compare KERNEL predictions against independent reference annotations for the same AOI and temporal period. Report precision, recall, F1 and/or ROC-AUC; describe the threshold selection; and disclose class imbalance and footprint coverage. Research-paper metrics must not be presented as KERNEL's own validation results.
