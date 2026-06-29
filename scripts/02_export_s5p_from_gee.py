import os
import sys
from pathlib import Path

import ee

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from aqi_india.config import load_config, load_environment  # noqa: E402


def export_pollutant(name: str, spec: dict, cfg: dict) -> None:
    region_cfg = cfg["region"]
    start = cfg["date_range"]["start"]
    end = cfg["date_range"]["end"]
    export_folder = cfg["gee"]["export_folder"]
    scale = cfg["gee"]["scale_meters"]
    region = ee.Geometry.Rectangle(
        [region_cfg["west"], region_cfg["south"], region_cfg["east"], region_cfg["north"]],
        proj="EPSG:4326",
        geodesic=False,
    )

    image = (
        ee.ImageCollection(spec["collection"])
        .filterDate(start, end)
        .filterBounds(region)
        .select(spec["band"])
        .mean()
        .clip(region)
    )

    description = f"{name}_{start}_{end}".replace("-", "")
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=export_folder,
        fileNamePrefix=description,
        region=region,
        scale=scale,
        crs="EPSG:4326",
        maxPixels=1_000_000_000_000,
    )
    task.start()
    print(f"Started export task: {description}")


def main() -> None:
    load_environment()
    cfg = load_config()
    project = os.getenv("GEE_PROJECT")
    if not project:
        raise SystemExit("Missing GEE_PROJECT in .env")
    ee.Initialize(project=project)

    for name, spec in cfg["s5p"].items():
        export_pollutant(name, spec, cfg)

    print("Open https://code.earthengine.google.com/tasks to monitor exports.")


if __name__ == "__main__":
    main()
