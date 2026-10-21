"""Visual generator producing dual localized thumbnails (ID & EN) in Base64 JPEG."""
import base64
import logging
import os
import random
from io import BytesIO
import httpx
from PIL import Image, ImageDraw, ImageFont
from config.settings import settings

logger = logging.getLogger("ImageGenerator")


def get_pexels_image(query: str) -> Image.Image | None:
    """Cari stok foto 1400x700 dari Pexels API."""
    api_key = settings.PEXELS_KEY or os.getenv("PEXELS_KEY")
    if not api_key:
        return None
    try:
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
        headers = {"Authorization": api_key}
        with httpx.Client(timeout=15.0) as client:
            res = client.get(url, headers=headers)
            data = res.json()
            if data.get("photos"):
                raw_url = data["photos"][0]["src"]["original"]
                img_url = f"{raw_url}?auto=compress&cs=tinysrgb&w=1400&h=700&fit=crop"
                img_res = client.get(img_url)
                return Image.open(BytesIO(img_res.content))
    except Exception as e:
        logger.warning(f"Pexels Error: {e}")
    return None


def generate_flux_image(prompt: str) -> Image.Image | None:
    """Fallback generate gambar via Pollinations AI (Flux Schnell Model)."""
    seed = random.randint(0, 99999)
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1400&height=700&seed={seed}&model=flux-schnell&nologo=true"
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(url)
            if res.status_code == 200:
                return Image.open(BytesIO(res.content))
    except Exception as e:
        logger.warning(f"AI Image Error: {e}")
    return None


def add_text_overlay(base_img: Image.Image, title_text: str) -> Image.Image:
    """
    Menempelkan teks judul dengan margin aman 16% dan gradasi gelap
    agar tahan terhadap crop rasio kartu web di frontend.
    """
    img = base_img.copy()
    width, height = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. SAFE MARGIN ZONE (16% padding kiri & kanan)
    margin_x = int(width * 0.16)         # ~224px pada lebar 1400px
    max_text_width = int(width * 0.68)    # Batas lebar area teks

    # 2. Gradasi Gelap di Sisi Kiri
    for x in range(int(width * 0.80)):
        alpha = int(240 * (1 - (x / (width * 0.80)) ** 1.3))
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))

    # 3. Dynamic Font Scaling (Otomatis mengecil jika judul panjang)
    cleaned_title = title_text.strip()
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arial.ttf",
    ]
    font_path = next((p for p in font_paths if os.path.exists(p)), None)

    if len(cleaned_title) > 45:
        font_size = 48
    elif len(cleaned_title) > 28:
        font_size = 56
    else:
        font_size = 66

    try:
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
            brand_font = ImageFont.truetype(font_path, 28)
        else:
            font = ImageFont.load_default()
            brand_font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
        brand_font = ImageFont.load_default()

    # 4. Branding Watermark "kodepintar."
    draw.text((margin_x, 90), "kodepintar.", fill=(255, 255, 255, 230), font=brand_font)
    draw.line([(margin_x, 130), (margin_x + 60, 130)], fill=(255, 255, 255, 140), width=3)

    # 5. Word Wrapping Presisi
    words = cleaned_title.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_text_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    lines = lines[:3]  # Maksimal 3 baris agar tidak meluap ke bawah

    # 6. Posisi Teks Vertikal di Safe Zone
    line_height = font.getbbox("Ay")[3] + 16 if hasattr(font, "getbbox") else 50
    total_h = len(lines) * line_height
    start_y = (height // 2) - (total_h // 2) + 40

    for i, line in enumerate(lines):
        draw.text((margin_x, start_y + (i * line_height)), line, fill=(255, 255, 255, 255), font=font)

    combined = Image.alpha_composite(img.convert("RGBA"), overlay)
    return combined.convert("RGB")


def image_to_base64(img: Image.Image) -> str:
    buffered = BytesIO()
    img.save(buffered, format="JPEG", quality=85, optimize=True)
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"


def generate_dual_thumbnails(id_title: str, en_title: str, keyword: str) -> tuple[str, str]:
    """
    Mengambil 1 gambar dasar lalu merender 2 thumbnail terpisah (ID & EN) di memori.
    Pipeline 3 tahap: Pexels API -> Pollinations Flux AI -> Dark Solid Background RGB(24, 24, 27).
    """
    logger.info(f"🎨 [IMAGE] Mencari visual dasar untuk keyword: '{keyword}'...")
    base_img = get_pexels_image(keyword)

    if not base_img:
        logger.info("🎨 [IMAGE] Pexels tidak tersedia/kosong, membuat visual via Flux AI...")
        prompt = f"Minimalist clean technology concept, {keyword}, modern sleek aesthetic, 8k, no text"
        base_img = generate_flux_image(prompt)

    if not base_img:
        logger.info("🎨 [IMAGE] Menggunakan solid dark background RGB(24, 24, 27).")
        base_img = Image.new("RGB", (1400, 700), color=(24, 24, 27))

    # Pastikan ukuran persis 1400x700
    if base_img.size != (1400, 700):
        base_img = base_img.resize((1400, 700), Image.Resampling.LANCZOS)

    # Render terpisah untuk ID dan EN
    img_id = add_text_overlay(base_img, id_title)
    img_en = add_text_overlay(base_img, en_title)

    return image_to_base64(img_id), image_to_base64(img_en)

