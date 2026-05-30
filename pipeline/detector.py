from ultralytics import YOLO
from pipeline.models import Detection


class YOLOv8Detector:
    """Wrapper class around YOLOv8 for running person detection on single frames."""

    def __init__(self, model_name: str = "yolov8n.pt"):
        self.model = YOLO(model_name)

    def detect(self, frame) -> list[Detection]:
        """Runs person detection (class ID 0) on the input frame."""
        results = self.model(frame, classes=[0], verbose=False)
        detections = []
        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        class_id=cls,
                    )
                )
        return detections
