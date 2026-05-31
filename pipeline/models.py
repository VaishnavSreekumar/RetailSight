from dataclasses import dataclass, field
import uuid


@dataclass
class Detection:
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int


@dataclass
class Track:
    track_id: int
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)
    confidence: float


@dataclass
class GeneratedEvent:
    event_type: str
    visitor_id: str
    store_id: str
    timestamp: str  # ISO-8601 string
    confidence: float
    event_id: str = field(default_factory=lambda: "")
    zone_id: str | None = None
    dwell_ms: int | None = None
    camera_id: str | None = None

    def __post_init__(self):
        unique_string = f"{self.store_id}:{self.camera_id or ''}:{self.visitor_id}:{self.event_type}:{self.timestamp}:{self.zone_id or ''}"
        self.event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

    def to_dict(self) -> dict:
        data = {
            "event_id": self.event_id,
            "store_id": self.store_id,
            "visitor_id": self.visitor_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "confidence": round(self.confidence, 4),
        }
        if self.zone_id is not None:
            data["zone_id"] = self.zone_id
        if self.dwell_ms is not None:
            data["dwell_ms"] = self.dwell_ms
        if self.camera_id is not None:
            data["camera_id"] = self.camera_id
        return data
