import json
from pathlib import Path
from shapely.geometry import Polygon

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurable thresholds
MIN_DWELL_SECONDS = 5.0
EXIT_TIMEOUT_FRAMES = 30
ZONE_CHANGE_DEBOUNCE_FRAMES = 10


def load_zones_config(config_path: str | Path | None = None) -> dict:
    """Loads and returns Shapely Polygons for store zones from a config file."""
    if config_path is None:
        config_path = BASE_DIR / "pipeline" / "sample_store_config" / "zones.json"

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Zone configuration file not found at: {config_path}")

    with open(config_path, "r") as f:
        data = json.load(f)

    # Construct Shapely Polygons
    zones = {
        "entry_zone": Polygon(data["entry_zone"]),
        "billing_zone": Polygon(data["billing_zone"]),
        "retail_zones": {
            zone_id: Polygon(coords)
            for zone_id, coords in data.get("retail_zones", {}).items()
        },
    }
    return zones
