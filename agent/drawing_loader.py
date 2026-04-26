import base64
import json
import re
from pathlib import Path

import anthropic
import pandas as pd

EXTRACT_PROMPT = (
    "This is an engineering drawing or equipment schedule for a mining or energy facility. "
    "Extract every equipment tag and its description as shown. "
    "Return a JSON array of objects, each with 'tag' (e.g. PP-001) and 'description'. "
    "Only include items with a clearly identifiable tag number. "
    "Return only the JSON array with no other text."
)


def _query_claude_vision(img_b64: str, media_type: str) -> pd.DataFrame:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": EXTRACT_PROMPT},
            ],
        }],
    )
    text = message.content[0].text.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return pd.DataFrame(columns=["tag", "description"])
    try:
        items = json.loads(match.group())
        return pd.DataFrame(items) if items else pd.DataFrame(columns=["tag", "description"])
    except json.JSONDecodeError:
        return pd.DataFrame(columns=["tag", "description"])


def extract_from_image(image_path: str) -> pd.DataFrame:
    """Extract equipment data from a PNG or JPEG engineering drawing using Claude vision."""
    suffix = Path(image_path).suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    with open(image_path, "rb") as f:
        img_b64 = base64.standard_b64encode(f.read()).decode()
    return _query_claude_vision(img_b64, media_type)


def extract_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Extract equipment data from a PDF engineering drawing using Claude vision.
    Each page is processed separately and results are combined."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    frames = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_b64 = base64.standard_b64encode(pix.tobytes("png")).decode()
        frames.append(_query_claude_vision(img_b64, "image/png"))
    doc.close()
    if not frames:
        return pd.DataFrame(columns=["tag", "description"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["tag"])


def extract_from_dxf(dxf_path: str) -> pd.DataFrame:
    """Extract equipment data from a DXF CAD file by reading block INSERT attributes.
    Looks for common attribute tag names used in engineering block libraries."""
    import ezdxf

    TAG_ATTRS = {"TAG_NO", "TAG", "EQUIP_NO", "ITEM_NO", "NUMBER"}
    DESC_ATTRS = {"EQUIP_DESC", "DESCRIPTION", "DESC", "NAME", "TITLE"}

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    rows = []
    for entity in msp:
        if entity.dxftype() == "INSERT" and entity.attribs:
            tag_val = desc_val = None
            for attrib in entity.attribs:
                attr_name = attrib.dxf.tag.upper()
                if attr_name in TAG_ATTRS:
                    tag_val = attrib.dxf.text.strip()
                elif attr_name in DESC_ATTRS:
                    desc_val = attrib.dxf.text.strip()
            if tag_val:
                rows.append({"tag": tag_val, "description": desc_val})

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["tag", "description"])


def load_drawings_from_directory(drawings_dir: str) -> pd.DataFrame:
    """Scan a directory and extract equipment data from all supported drawing files.
    Supports: .png, .jpg, .jpeg (via Claude vision), .pdf (via Claude vision), .dxf (via ezdxf).
    3D model formats (.stp, .step, .obj) require a render to image before processing."""
    path = Path(drawings_dir)
    frames = []

    for file in sorted(path.iterdir()):
        suffix = file.suffix.lower()
        print(f"  Loading drawing: {file.name}")
        if suffix in (".png", ".jpg", ".jpeg"):
            df = extract_from_image(str(file))
            df["file_type"] = "image"
            frames.append(df)
        elif suffix == ".pdf":
            df = extract_from_pdf(str(file))
            df["file_type"] = "pdf"
            frames.append(df)
        elif suffix == ".dxf":
            df = extract_from_dxf(str(file))
            df["file_type"] = "cad"
            frames.append(df)
        else:
            print(f"  Skipping unsupported format: {file.name}")

    if not frames:
        return pd.DataFrame(columns=["tag", "description", "file_type"])
    return (
        pd.concat(frames, ignore_index=True)
        .dropna(subset=["tag"])
        .drop_duplicates(subset=["tag", "file_type"])
    )
