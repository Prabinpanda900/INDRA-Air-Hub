import os
import sys
from pathlib import Path

import ee

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from aqi_india.config import load_environment  # noqa: E402


def main() -> None:
    load_environment()
    project = os.getenv("GEE_PROJECT")
    if not project:
        raise SystemExit("Missing GEE_PROJECT in .env")
    ee.Initialize(project=project)
    message = ee.String("Earth Engine initialized successfully.").getInfo()
    print(message)


if __name__ == "__main__":
    main()
