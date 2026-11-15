
import ee
import pwtt

ee.Initialize(project="battle-damage-assessment")

aoi = ee.Geometry.Rectangle([
    37.949421,
    48.556181,
    38.043834,
    48.621584
])

print("Starting PWTT with export enabled...")

result = pwtt.detect_damage(
    aoi=aoi,
    war_start="2022-02-22",
    inference_start="2024-07-01",
    pre_interval=12,
    post_interval=1,
    viz=False,
    export=True,
    export_dir="PWTT_Export",
    export_name="Kernel_Bakhmut",
    export_scale=10
)

print("PWTT processing and export call completed!")
