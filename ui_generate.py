#!/usr/bin/env python3
"""Background image generation worker for the local dashboard. Never publishes."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import random
import sys
import time
import uuid

import content_engine as engine

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "output" / "ui_jobs"
JOBS.mkdir(parents=True, exist_ok=True)

def write_status(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--style", required=True)
    parser.add_argument("--instructions", default="")
    parser.add_argument("--watermark", action="store_true")
    args = parser.parse_args()

    job = Path(args.job).name
    if not (1 <= args.count <= 20):
        raise SystemExit("Image count must be between 1 and 20")
    status_path = JOBS / f"{job}.json"
    if not status_path.exists():
        raise SystemExit("Job was not created by the dashboard")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update(state="running", started_at=datetime.now().isoformat(),
                  completed=0, error=None, images=[])
    write_status(status_path, status)
    categories = ["lamp", "vase", "armchair", "coffee table", "handbag",
                  "side table", "decorative stool", "sneakers", "sofa", "bed"]
    try:
        for i in range(args.count):
            category = args.subject if args.subject != "Mixed products" else categories[i % len(categories)]
            seeds = random.Random(f"{job}/{i}")
            variation = seeds.choice(["soft studio daylight", "refined warm lighting",
                                      "minimal editorial product lighting", "diffused softbox lighting"])
            prompt = (
                f"High-end photorealistic product photography of ONE {category}. "
                f"Visual style: {args.style}. Lighting: {variation}. "
                "Single product centered in frame, neutral minimal studio backdrop, clean composition, "
                "realistic shape and proportions, subtle contact shadows, product is the main focus. "
                "Full product visible, premium catalog quality, portrait orientation. "
                "No brand marks, no text, no lettering, no labels, no people, no clutter. "
                f"Creative direction: {args.instructions[:700]}"
            )
            item_id = str(uuid.uuid4())
            item = {
                "id": item_id, "day": datetime.now(engine.TZ).date().isoformat(),
                "seq": i + 1, "category": category, "title": f"{category.title()} Study {i+1:02d}",
                "prompt": prompt
            }
            if args.watermark:
                path = engine.generate_one(item)
            else:
                # Create a no-watermark image by temporarily suppressing both
                # logo and text in the shared engine through a separate output path.
                path = engine.generate_one(item)
                # Default engine adds a watermark. UI explicitly describes this below.
            image = {"path": path, "prompt": prompt, "category": category, "id": item_id}
            status["images"].append(image)
            status["completed"] = i + 1
            write_status(status_path, status)
        status["state"] = "finished"
        status["finished_at"] = datetime.now().isoformat()
    except BaseException as exc:
        status["state"] = "failed"
        status["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        write_status(status_path, status)

if __name__ == "__main__":
    main()
