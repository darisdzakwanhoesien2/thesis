import base64
from pathlib import Path
from io import BytesIO
from PIL import Image


def extract_pages(result_json):
    if "data" in result_json and "pages" in result_json["data"]:
        return result_json["data"]["pages"]
    if "pages" in result_json:
        return result_json["pages"]
    if "results" in result_json and "pages" in result_json["results"]:
        return result_json["results"]["pages"]

    raise RuntimeError("Unknown OCR response format")


def save_pages_and_images(pages, base_dir: Path):

    pages_dir = base_dir / "pages"
    images_dir = base_dir / "images"

    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    for p in pages:
        idx = p.get("index", 0)

        # ---------- Markdown ----------
        md = p.get("markdown", "")
        md_file = pages_dir / f"page_{idx:03d}.md"
        md_file.write_text(md, encoding="utf-8")

        # ---------- Images ----------
        images = []

        if "images" in p:
            images = p["images"]
        elif "blocks" in p:
            images = [b for b in p["blocks"] if "image_base64" in b]

        for i, img in enumerate(images):
            b64 = img.get("image_base64")
            if not b64:
                continue

            raw = base64.b64decode(b64.split(",")[-1])
            im = Image.open(BytesIO(raw)).convert("RGB")

            img_path = images_dir / f"page_{idx}_img_{i+1}.jpg"
            im.save(img_path)
