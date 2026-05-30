from shapely.geometry import Point
from pipeline.models import Track


class ZoneEngine:
    """Polygon-based spatial analysis engine for mapping tracked visitors to retail zones."""

    def __init__(self, zones: dict):
        self.entry_zone = zones["entry_zone"]
        self.billing_zone = zones["billing_zone"]
        self.retail_zones = zones["retail_zones"]

    def get_bottom_center(self, bbox: tuple[float, float, float, float]) -> Point:
        """Calculates the center-bottom coordinate of the tracked bounding box."""
        x1, y1, x2, y2 = bbox
        return Point((x1 + x2) / 2.0, y2)

    def is_in_entry(self, track: Track) -> bool:
        """Checks if the tracked visitor bottom center is in the entry zone polygon."""
        pt = self.get_bottom_center(track.bbox)
        return self.entry_zone.contains(pt)

    def is_in_billing(self, track: Track) -> bool:
        """Checks if the tracked visitor bottom center is in the checkout/billing zone polygon."""
        pt = self.get_bottom_center(track.bbox)
        return self.billing_zone.contains(pt)

    def get_retail_zone(self, track: Track) -> str | None:
        """Returns the retail zone identifier if the visitor is within any retail polygon."""
        pt = self.get_bottom_center(track.bbox)
        for zone_id, poly in self.retail_zones.items():
            if poly.contains(pt):
                return zone_id
        return None
