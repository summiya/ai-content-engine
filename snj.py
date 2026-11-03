#!/usr/bin/env python3
"""Local AI furniture content engine: python snj.py doctor|demo|daily|publish|run|status."""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timedelta
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import random
import sys
import time
import uuid
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
(ROOT / "output").mkdir(exist_ok=True)
(ROOT / "logs").mkdir(exist_ok=True)
logging.basicConfig(filename=ROOT / "logs" / "snj.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
DB = ROOT / "output" / "queue.json"
TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Dubai"))

CATEGORIES = [
    ("bed", 5), ("sofa", 4), ("side table", 3), ("accent chair", 3),
    ("coffee table", 2), ("ottoman", 2), ("TV console", 1)
]
DESIGNS = {
    "bed": ["rounded channel-tufted headboard with mattress-free dark support platform",
            "minimal wingback headboard with light linen upholstery and mattress-free base",
            "soft modern scalloped headboard and bare black support platform",
            "low platform bed with smooth cream upholstered frame and no mattress",
            "vertical-panel headboard and slim floating-look base without bedding"],
    "sofa": ["three-seat sofa with rounded arms", "low-profile curved loveseat",
             "modular sectional in two sections", "contemporary bench-seat sofa"],
    "side table": ["round oak two-drawer nightstand", "cylindrical walnut nightstand",
                   "matte ivory bedside cabinet", "black stained-oak side table"],
    "accent chair": ["bouclé barrel chair", "curved upholstered lounge chair",
                     "minimal sculptural occasional chair"],
    "coffee table": ["oval warm oak coffee table", "rounded travertine-look coffee table"],
    "ottoman": ["round bouclé ottoman", "sculptural upholstered stool"],
    "TV console": ["long floating-look oak TV console with handleless doors"]
}
COLORS = ["warm ivory", "sand beige", "oatmeal", "taupe", "soft charcoal",
          "muted stone", "natural oak"]
MATERIALS = ["bouclé upholstery", "woven linen upholstery", "premium velvet-look upholstery",
             "natural oak veneer", "matte lacquer finish", "textured fabric upholstery"]
CTA = [
    "Message us on Instagram to discuss made-to-order options in Dubai.",
    "DM SNJ Interiors for custom sizing and finish enquiries.",
    "Looking for a tailored finish? Send us a DM.",
    "Ask us about custom dimensions and available materials via DM."
]
HASHTAGS = "#SNJInteriors #DubaiFurniture #CustomFurnitureDubai #MadeToOrderFurniture #DubaiInteriors"


def now():
    return datetime.now(TZ)


def load_db():
    if DB.exists():
        return json.loads(DB.read_text(encoding="utf8"))
    return {"items": []}


def save_db(data):
    tmp = DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf8")
    tmp.replace(DB)


@contextmanager
def single_instance():
    import fcntl
    fp = (ROOT / "output" / ".lock").open("a+")
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another run is active; exiting without overlap.")
        fp.close()
        sys.exit(0)
    try:
        yield
    finally:
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        fp.close()


def font(size):
    for p in ["/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Supplemental/Helvetica.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def prepare_photo(image_bytes, destination):
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = ImageOps.fit(image, (1080, 1350),
                         method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    logo = ROOT / "assets" / "logo.png"
    if logo.exists():
        wm = Image.open(logo).convert("RGBA")
        wm.thumbnail((145, 65), Image.Resampling.LANCZOS)
        wm.putalpha(wm.getchannel("A").point(lambda p: int(p * 0.72)))
        image.paste(wm, (image.width - wm.width - 38, image.height - wm.height - 36), wm)
    else:
        draw = ImageDraw.Draw(image)
        label = os.getenv("WATERMARK_TEXT", "SNJ INTERIORS").strip() or "SNJ INTERIORS"
        f = font(21)
        bbox = draw.textbbox((0, 0), label, font=f)
        w = bbox[2] - bbox[0]
        draw.text((image.width - w - 36, image.height - 61),
                  label, font=f, fill=(95, 89, 82))
    image.save(destination, "JPEG", quality=91, optimize=True, subsampling=0)


def plan_for(day):
    seq = [category for category, qty in CATEGORIES for _ in range(qty)]
    random.Random(f"SNJ-{day}").shuffle(seq)
    count = int(os.getenv("DAILY_COUNT", "20"))
    if count < 1 or count > 40:
        raise ValueError("DAILY_COUNT must be between 1 and 40")
    if count > len(seq):
        seq = (seq * ((count + len(seq) - 1) // len(seq)))[:count]
    return seq[:count]


def schedule(day, count):
    start = int(os.getenv("POST_START_HOUR", "8"))
    end = int(os.getenv("POST_END_HOUR", "22"))
    if not (0 <= start < end <= 23):
        raise ValueError("Posting hours must satisfy 0 <= start < end <= 23")
    base = datetime.fromisoformat(day).replace(tzinfo=TZ, hour=start, minute=0)
    minutes = (end - start) * 60
    return [(base + timedelta(minutes=round(i * minutes / max(1, count - 1)))).isoformat()
            for i in range(count)]


def make_prompt(day, category, index):
    rnd = random.Random(f"{day}-{category}-{index}")
    design = DESIGNS[category][(index + int(day.replace("-", ""))) % len(DESIGNS[category])]
    return (
        f"Photorealistic premium e-commerce furniture product photograph of exactly ONE {category}: "
        f"{design}. Finish: {rnd.choice(COLORS)}; material inspiration: {rnd.choice(MATERIALS)}. "
        "Contemporary made-to-order Dubai furniture catalogue. Show the entire product from a "
        "straight-on or slight three-quarter product angle, well centered and large within the frame. "
        "Warm neutral beige seamless studio wall and floor, softly diffused studio lighting, "
        "subtle natural contact shadow, true-to-life proportions, precise construction details, "
        "uncluttered calm minimal style. NO other furniture, house plants, people, artwork, props, "
        "bold decor, watermarks, logos, letters, text, labels, or collages. For beds, show only "
        "the frame and headboard, NO mattress, NO pillows, NO bedding. "
        "Portrait composition suitable for cropping to 4:5. Make the product distinctive."
    )


def fallback_caption(item):
    title = item["title"]
    sentences = [
        f"{title} — a clean, contemporary furniture concept for considered spaces.",
        f"Meet {title}: subtle lines, versatile proportions and a refined minimalist look.",
        f"A fresh take on the {item['category']}: {title}, designed to inspire your next space.",
        f"{title}. Simple form, thoughtful detailing, and a warm, understated palette."
    ]
    rnd = random.Random(item["id"])
    return (f"{rnd.choice(sentences)}\n\n"
            "AI design concept shown; final specifications subject to manufacturer confirmation."
            f"\n\n{rnd.choice(CTA)}\n\n{HASHTAGS}")


def caption_for(item):
    if os.getenv("AI_CAPTIONS", "false").lower() != "true":
        return fallback_caption(item)
    from openai import OpenAI
    prompt = (
        f"Write ONE original Instagram caption for SNJ Interiors, a Dubai made-to-order furniture brand. "
        f"Product: {item['title']}, category: {item['category']}. "
        "Tone: tasteful, minimalist, concise, different from typical repetitive captions. "
        "2 short sentences max plus a direct message CTA. Do not promise exact prices, stock, "
        "manufacturing ability or lead times. Include the exact phrase "
        "'AI design concept; subject to manufacturing confirmation.' "
        "End with 5 relevant hashtags. Return caption only."
    )
    try:
        reply = OpenAI().responses.create(
            model=os.getenv("OPENAI_CAPTION_MODEL", "gpt-5-mini"), input=prompt)
        value = reply.output_text.strip()
        return value if value else fallback_caption(item)
    except Exception as exc:
        logging.warning("AI caption fallback: %s", exc)
        return fallback_caption(item)


def generate_one(item):
    from openai import OpenAI
    client = OpenAI(timeout=240.0, max_retries=2)
    result = client.images.generate(
        model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        prompt=item["prompt"], size="1024x1536",
        quality=os.getenv("OPENAI_IMAGE_QUALITY", "medium"),
        n=1, output_format="jpeg"
    )
    raw = base64.b64decode(result.data[0].b64_json)
    directory = ROOT / "output" / item["day"]
    directory.mkdir(exist_ok=True, parents=True)
    dest = directory / f"{item['seq']:02d}_{item['category'].replace(' ', '_')}_{item['id'][:8]}.jpg"
    prepare_photo(raw, dest)
    return str(dest.relative_to(ROOT))


def daily():
    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY in .env")
        return
    today = now().date().isoformat()
    db = load_db()
    planned = plan_for(today)
    times = schedule(today, len(planned))
    for i, category in enumerate(planned):
        if any(x["day"] == today and x["seq"] == i + 1 for x in db["items"]):
            continue
        item = {
            "id": str(uuid.uuid4()), "day": today, "seq": i + 1,
            "category": category,
            "title": f"SNJ {category.title()} Concept {today.replace('-', '')}-{i+1:02d}",
            "prompt": make_prompt(today, category, i), "schedule": times[i],
            "status": "generating", "path": None, "caption": None
        }
        db["items"].append(item)
        save_db(db)
    for item in db["items"]:
        if item["day"] != today or item["status"] != "generating":
            continue
        try:
            print(f"Generating {item['seq']}/{len(planned)}: {item['category']}", flush=True)
            item["path"] = generate_one(item)
            item["caption"] = caption_for(item)
            item["status"] = "ready"
            item["error"] = None
            print("Saved:", item["path"], flush=True)
        except Exception as exc:
            item["status"] = "generation_error"
            item["error"] = str(exc)
            logging.exception("Failed image %s", item["id"])
            print("Generation error:", exc, flush=True)
        finally:
            save_db(db)
    print("Daily generation completed. Review images in output/", today)


def graph(method, endpoint, data=None, timeout=60):
    import requests
    host = os.getenv("META_API_HOST", "graph.facebook.com")
    version = os.getenv("META_API_VERSION", "v24.0")
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN is missing")
    url = f"https://{host}/{version}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {token}"}
    if method == "POST":
        response = requests.post(url, data=data or {}, headers=headers, timeout=timeout)
    else:
        response = requests.get(url, params=data or {}, headers=headers, timeout=timeout)
    try:
        payload = response.json()
    except ValueError:
        response.raise_for_status()
        raise RuntimeError("Unexpected non-JSON response from Meta")
    if not response.ok or "error" in payload:
        raise RuntimeError(f"Meta API error: {json.dumps(payload, ensure_ascii=False)[:1000]}")
    return payload


def quota_check():
    ig = os.getenv("IG_USER_ID")
    data = graph("GET", f"{ig}/content_publishing_limit")
    rows = data.get("data", [])
    if not rows:
        raise RuntimeError("Instagram did not return publishing quota data: " + repr(data))
    quota = rows[0].get("quota_usage")
    cap = int(os.getenv("DAILY_SAFETY_CAP", "20"))
    if quota is None:
        raise RuntimeError("Could not read quota usage; refusing to post")
    if int(quota) >= cap:
        raise RuntimeError(f"Publishing safety cap reached: {quota}/{cap} in moving 24h")
    return quota


def cloudinary_upload(item):
    import cloudinary.uploader
    if not os.getenv("CLOUDINARY_URL"):
        raise RuntimeError("CLOUDINARY_URL missing from .env")
    path = ROOT / item["path"]
    if not path.exists():
        raise FileNotFoundError(path)
    result = cloudinary.uploader.upload(str(path), folder="snj-instagram",
                                         resource_type="image", overwrite=False)
    return result["secure_url"], result["public_id"]


def persist_item(item):
    db = load_db()
    for index, prior in enumerate(db["items"]):
        if prior["id"] == item["id"]:
            db["items"][index] = item
            save_db(db)
            return
    raise RuntimeError("Queue item not found")


def instagram_publish(item):
    ig = os.getenv("IG_USER_ID")
    if not ig:
        raise RuntimeError("IG_USER_ID missing")
    if not item.get("public_url"):
        url, public_id = cloudinary_upload(item)
        item["public_url"] = url
        item["cloudinary_public_id"] = public_id
        item["status"] = "uploaded"
        persist_item(item)
    else:
        url = item["public_url"]
    if not item.get("container_id"):
        response = graph("POST", f"{ig}/media", {
            "image_url": url, "caption": item["caption"],
            "alt_text": f"Minimal studio product design concept: {item['title']}"
        })
        item["container_id"] = response["id"]
        item["status"] = "container_created"
        persist_item(item)
    cid = item["container_id"]
    for _ in range(12):
        state_response = graph("GET", cid, {"fields": "status_code,status"})
        state = state_response.get("status_code")
        if state == "FINISHED":
            break
        if state in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container {cid}: {state_response}")
        time.sleep(5)
    else:
        raise RuntimeError("Container still processing; will retry later")
    # Store uncertain state BEFORE publish to avoid duplicates on lost responses.
    item["status"] = "publish_uncertain"
    persist_item(item)
    response = graph("POST", f"{ig}/media_publish", {"creation_id": cid})
    item["status"] = "published"
    item["instagram_media_id"] = response["id"]
    item["published_at"] = now().isoformat()
    persist_item(item)


def publish():
    db = load_db()
    due = [
        x for x in db["items"]
        if x["status"] in ("ready", "uploaded", "container_created")
        and datetime.fromisoformat(x["schedule"]) <= now()
    ]
    if not due:
        print("Nothing due for publishing.")
        return
    if os.getenv("AUTO_PUBLISH", "false").lower() != "true":
        print(f"Preview mode: {len(due)} due posts; AUTO_PUBLISH=false, nothing sent.")
        return
    if not all(os.getenv(x) for x in ("IG_USER_ID", "META_ACCESS_TOKEN", "CLOUDINARY_URL")):
        print("Publishing credentials incomplete; nothing posted.")
        return
    item = sorted(due, key=lambda x: x["schedule"])[0]
    try:
        quota_check()
        print(f"Publishing {item['title']}...")
        instagram_publish(item)
        print("Published:", item.get("instagram_media_id"))
    except Exception as exc:
        item["error"] = str(exc)
        persist_item(item)
        logging.exception("Publish error %s", item["id"])
        if item["status"] == "publish_uncertain":
            print("PUBLISH RESULT UNCERTAIN. Check Instagram before manual recovery.")
        print("Publish error:", exc)


def demo():
    image = Image.new("RGB", (1024, 1536), "#e9e2dc")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((150, 630, 874, 1050), radius=90, fill="#c9bbad")
    for x in range(230, 850, 95):
        draw.line((x, 660, x, 1000), fill="#afa092", width=5)
    draw.rounded_rectangle((125, 1000, 900, 1150), radius=38, fill="#cfc2b4")
    draw.rectangle((165, 1010, 860, 1050), fill="#47413f")
    buffer = BytesIO()
    image.save(buffer, "PNG")
    destination = ROOT / "output" / "DEMO_SNJ_watermark.jpg"
    prepare_photo(buffer.getvalue(), destination)
    print("Offline mockup created:", destination)


def doctor():
    print("Mac configuration check (secrets hidden)")
    for name in ("OPENAI_API_KEY", "IG_USER_ID", "META_ACCESS_TOKEN", "CLOUDINARY_URL"):
        print(f"  {name}: {'configured' if os.getenv(name) else 'MISSING'}")
    print("  AUTO_PUBLISH:", os.getenv("AUTO_PUBLISH", "false"))
    print("  IMAGE_MODEL:", os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"))
    print("  LOCAL_TIME:", now().isoformat())
    if os.getenv("IG_USER_ID") and os.getenv("META_ACCESS_TOKEN"):
        try:
            account = graph("GET", os.getenv("IG_USER_ID"), {"fields": "id,username"})
            print("  META_TEST:", account)
            print("  QUOTA_USAGE:", quota_check())
        except Exception as exc:
            print("  META_TEST_FAILED:", exc)


def status():
    from collections import Counter
    db = load_db()
    print("Items:", len(db["items"]))
    print("Status:", dict(Counter(item["status"] for item in db["items"])))
    for item in db["items"][-8:]:
        print(item["day"], item["seq"], item["category"],
              item["status"], item.get("error", ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "demo", "daily", "publish", "run", "status"])
    args = parser.parse_args()
    with single_instance():
        if args.command == "doctor":
            doctor()
        elif args.command == "demo":
            demo()
        elif args.command == "daily":
            daily()
        elif args.command == "publish":
            publish()
        elif args.command == "run":
            daily()
            publish()
        elif args.command == "status":
            status()


if __name__ == "__main__":
    main()
