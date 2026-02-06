from pathlib import Path


def list_pdf_folders(base_dir="outputs"):
    base = Path(base_dir)
    if not base.exists():
        return []
    return [p for p in base.iterdir() if p.is_dir() and p.name.endswith("_pdf")]


def list_md_pages(pdf_folder):
    pages_dir = Path(pdf_folder) / "pages"
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("page_*.md"))


# import uuid
# from pathlib import Path

# OUT_DIR = Path("outputs")
# OUT_DIR.mkdir(exist_ok=True)


# def save_upload(uploaded_file):
#     ext = Path(uploaded_file.name).suffix
#     path = OUT_DIR / f"{uuid.uuid4()}{ext}"

#     with open(path, "wb") as f:
#         f.write(uploaded_file.getbuffer())

#     return path


# def save_text(text):
#     path = OUT_DIR / f"ocr_{uuid.uuid4()}.txt"
#     path.write_text(text, encoding="utf-8")
#     return path


# import uuid
# from pathlib import Path


# TMP_DIR = Path("outputs")
# TMP_DIR.mkdir(exist_ok=True)


# def save_uploaded_file(uploaded_file):
#     suffix = Path(uploaded_file.name).suffix
#     path = TMP_DIR / f"{uuid.uuid4()}{suffix}"

#     with open(path, "wb") as f:
#         f.write(uploaded_file.getbuffer())

#     return path


# def save_text(text: str):
#     path = TMP_DIR / f"ocr_{uuid.uuid4()}.txt"
#     path.write_text(text, encoding="utf-8")
#     return path