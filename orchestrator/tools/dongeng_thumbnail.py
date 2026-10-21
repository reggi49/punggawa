"""Thumbnail processor for Dongeng CMS (Bogorstore) portrait format (200x300)."""
import logging
import os
import re
import tempfile
import uuid
from io import BytesIO
import httpx
from PIL import Image, ImageDraw, ImageFont

from config.settings import settings

logger = logging.getLogger("DongengThumbnail")

THUMB_WIDTH = 200
THUMB_HEIGHT = 300


def sanitize_text(text: str) -> str:
    """Membersihkan teks dari emoji dan karakter non-ASCII yang menyebabkan font kotak-kotak."""
    if not text:
        return ""
    clean = re.sub(r"[^\x20-\x7E]", "", text)
    return clean.strip()


def load_font(font_path: str, size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Memuat font TrueType dengan fallback otomatis jika path Linux tidak tersedia di macOS."""
    candidate_paths = [
        font_path,
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf",
    ]
    for p in candidate_paths:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue

    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def wrap_text(text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrapping dengan batas lebar piksel, maksimal 2 baris (dengan ellipsis jika panjang)."""
    tmp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words = text.split(" ")
    lines: list[str] = []
    current_line: list[str] = []

    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        if tmp_draw.textlength(test_line, font=font) <= max_width:
            pass
        else:
            if current_line:
                current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    # Batasi maksimal 2 baris
    if len(lines) > 2:
        lines = lines[:2]
        if len(lines[1]) > 3:
            lines[1] = lines[1][:-3] + "..."

    return lines


def create_cms_thumbnail(
    image_url: str,
    short_title: str,
    output_filename: str | None = None,
) -> str | None:
    """
    Mengunduh gambar YouTube latar, memotong black bar 12.5%,
    melakukan center-crop ke rasio 2:3 (200x300), lalu menempelkan overlay gelap + judul.
    """
    # 1. Fallback multi-resolusi jika gambar utama gagal
    candidate_urls = [image_url]
    for res in ("maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"):
        alt = re.sub(r"/[a-z]+default\.jpg$", f"/{res}.jpg", image_url)
        if alt not in candidate_urls:
            candidate_urls.append(alt)

    img_orig = None
    with httpx.Client(timeout=15.0) as client:
        for url in candidate_urls:
            try:
                resp = client.get(url)
                if resp.status_code == 200:
                    img_orig = Image.open(BytesIO(resp.content))
                    img_orig.load()  # Verifikasi gambar valid
                    break
            except Exception:
                continue

    if img_orig is None:
        logger.error(f"Gagal mengunduh thumbnail dari semua URL kandidat: {candidate_urls}")
        return None

    try:
        orig_w, orig_h = img_orig.size
        # Potong letterbox hitam atas & bawah 12.5%
        black_bar_height = int(orig_h * 0.125)
        clean_h = orig_h - (2 * black_bar_height)

        # Hitung rasio target 2:3 (200x300)
        target_ratio = THUMB_WIDTH / THUMB_HEIGHT
        crop_width = clean_h * target_ratio

        left = (orig_w - crop_width) / 2
        right = (orig_w + crop_width) / 2
        top = black_bar_height
        bottom = orig_h - black_bar_height

        img_cropped = img_orig.crop((left, top, right, bottom))
        img = img_cropped.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Muat font
        font_title = load_font(settings.DONGENG_FONT_PATH, 16)
        max_text_width = THUMB_WIDTH - 20

        # Bersihkan emoji dan wrap judul
        clean_title = sanitize_text(short_title)
        wrapped_lines = wrap_text(clean_title, font_title, max_text_width)

        line_height = 20
        text_box_height = (len(wrapped_lines) * line_height) + 20

        # Overlay semi-transparan hitam di bagian bawah
        overlay = Image.new("RGBA", (THUMB_WIDTH, int(text_box_height)), (0, 0, 0, 170))
        img.paste(overlay, (0, THUMB_HEIGHT - int(text_box_height)), overlay)

        # Tulis teks di atas overlay (rata tengah)
        current_y = THUMB_HEIGHT - int(text_box_height) + 10
        for line in wrapped_lines:
            line_w = draw.textlength(line, font=font_title)
            x_pos = (THUMB_WIDTH - line_w) / 2
            draw.text((x_pos, current_y), line, font=font_title, fill="white")
            current_y += line_height

        # Simpan ke file output
        if not output_filename:
            temp_dir = tempfile.gettempdir()
            output_filename = os.path.join(temp_dir, f"thumb_dongeng_{uuid.uuid4().hex[:8]}.jpg")

        img.convert("RGB").save(output_filename, format="JPEG", quality=90)
        logger.info(f"Thumbnail CMS berhasil dibuat: {output_filename}")
        return output_filename

    except Exception as exc:
        logger.error(f"Gagal merender thumbnail portrait: {exc}", exc_info=True)
        return None

