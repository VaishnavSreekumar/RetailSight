import argparse
import json
import sys
from pathlib import Path
import cv2

# Add parent directory to sys.path to allow importing from pipeline
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pipeline.config import (
    EXIT_TIMEOUT_FRAMES,
    MIN_DWELL_SECONDS,
    ZONE_CHANGE_DEBOUNCE_FRAMES,
    load_zones_config,
)
from pipeline.event_generator import EventGenerator
from pipeline.tracker import YOLOv8Tracker
from pipeline.zones import ZoneEngine


def run_pipeline(
    video_path: str,
    output_path: str,
    store_id: str,
    model_path: str = "yolov8n.pt",
    camera_id: str | None = None,
    max_frames: int | None = None,
    config_path: str | None = None,
):
    """Executes the CV detection and tracking pipeline over a video file."""
    # 1. Load configurations
    zones = load_zones_config(config_path)
    zone_engine = ZoneEngine(zones)

    # 2. Initialize tracking & event generation
    tracker = YOLOv8Tracker(model_name=model_path)
    generator = EventGenerator(
        zone_engine=zone_engine,
        store_id=store_id,
        exit_timeout_frames=EXIT_TIMEOUT_FRAMES,
        zone_debounce_frames=ZONE_CHANGE_DEBOUNCE_FRAMES,
        min_dwell_seconds=MIN_DWELL_SECONDS,
        camera_id=camera_id,
    )

    # 3. Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}", file=sys.stderr)
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    generator.fps = fps

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(
        f"Starting processing. Video: {video_path} | FPS: {fps:.2f} | Frames: {total_frames} | Store: {store_id}"
    )

    frame_idx = 0
    all_events = []

    # Process frames
    while True:
        if max_frames is not None and frame_idx >= max_frames:
            break

        ret, frame = cap.read()
        if not ret:
            break

        # Get tracked entities on this frame
        tracks = tracker.track_frame(frame)

        # Generate events
        events = generator.process_frame(frame_idx, tracks)
        for e in events:
            all_events.append(e)
            print(
                f"[Frame {frame_idx}] Emitted event: {e.event_type} | Visitor: {e.visitor_id} | Zone: {e.zone_id}"
            )

        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx}/{total_frames} frames...")

    # Capture any final exits for tracks still active at video end
    final_events = generator.process_frame(frame_idx, [])
    for e in final_events:
        all_events.append(e)
        print(
            f"[Final] Emitted event: {e.event_type} | Visitor: {e.visitor_id} | Zone: {e.zone_id}"
        )

    cap.release()

    # 4. Write generated events to JSONL
    output_path = Path(output_path)
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for event in all_events:
            f.write(json.dumps(event.to_dict()) + "\n")

    print(
        f"Completed processing. Total events: {len(all_events)}. Output saved to: {output_path}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retail Intelligence CV Detection MVP Pipeline"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Path to input MP4 video file."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="pipeline/output/events.jsonl",
        help="Path to write output events JSONL.",
    )
    parser.add_argument(
        "--store_id",
        type=str,
        default="STORE_BLR_002",
        help="Store identifier prefix.",
    )
    parser.add_argument(
        "--model", type=str, default="yolov8n.pt", help="YOLOv8 model weight name."
    )
    parser.add_argument(
        "--camera_id", type=str, default=None, help="Camera identifier."
    )
    parser.add_argument(
        "--max-frames", type=int, default=None, help="Maximum frames to process."
    )
    parser.add_argument(
        "--config-path", type=str, default=None, help="Path to zones configuration JSON."
    )
    args = parser.parse_args()

    run_pipeline(
        args.video,
        args.output,
        args.store_id,
        args.model,
        camera_id=args.camera_id,
        max_frames=args.max_frames,
        config_path=args.config_path,
    )
