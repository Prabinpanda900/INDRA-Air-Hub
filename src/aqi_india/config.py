from pathlib import Path

import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path = ROOT / "config" / "project_config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_environment() -> None:
    load_dotenv(ROOT / ".env")
