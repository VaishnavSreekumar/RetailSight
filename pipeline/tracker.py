from ultralytics import YOLO
from pipeline.models import Track


class YOLOv8Tracker:
    """Wrapper class leveraging YOLOv8's native tracking (ByteTrack/BoTSORT) capabilities."""

    def __init__(
        self, model_name: str = "yolov8n.pt", tracker_type: str = "bytetrack.yaml"
    ):
        self.model = YOLO(model_name)
        self.tracker_type = tracker_type

    def track_frame(self, frame) -> list[Track]:
        """Runs native object tracking for person detection (class ID 0) on the frame."""
        results = self.model.track(
            source=frame,
            persist=True,
            classes=[0],
            tracker=self.tracker_type,
            verbose=False,
        )
        tracks = []
        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                if box.id is not None:
                    track_id = int(box.id[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    tracks.append(
                        Track(
                            track_id=track_id,
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                        )
                    )
        return tracks
