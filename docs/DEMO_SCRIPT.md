# KERNEL hackathon demonstration script

1. Open the local dashboard and point out the Bakhmut study area and engine status.
2. Explain that the dashboard is reading local scored GeoJSON created from Sentinel-1 PWTT and building-footprint aggregation.
3. Show the total building count and candidates-for-review count returned by the API. Do not call candidates confirmed damaged buildings.
4. Click a building polygon. Explain its mean T-statistic, maximum T-statistic, valid raster pixels and screening status.
5. Open Satellite Comparison. Drag the reveal slider to compare the pre-event reference composite with the July 2024 inference composite. Toggle the PWTT T-statistic overlay.
6. Open Damage Analysis. Search/filter the scored building list and show how the screening results can be inspected.
7. Open Intelligence Reports and download the CSV.
8. Open New Assessment and explain that the submitted Earth Engine export is a processing task; exported rasters must be completed and scored before they become the current dashboard dataset.

## Safe claims

- KERNEL uses open Sentinel-1 radar data and a published unsupervised statistical method.
- The workflow turns pixel-level change indicators into building-level screening records.
- The map helps prioritize analyst review.

## Claims to avoid

- Do not say a flagged building is definitely destroyed.
- Do not claim the published paper's AUC/F1 values are KERNEL's measured accuracy.
- Do not describe a July 2024 inference composite as an immediate February 2022 post-event image.
- Do not imply the app autonomously verifies field damage.
