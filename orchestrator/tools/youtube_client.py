"""YouTube Data API v3 and RSS/Metadata Client for Dongeng Pipeline."""
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
import httpx

from config.settings import settings

logger = logging.getLogger("YouTubeClient")

YT_API = "https://www.googleapis.com/youtube/v3"

# Deteksi Shorts:
# - durasi <= SHORTS_MAX_SECONDS  -> pasti Short (gratis, tanpa HTTP).
# - SHORTS_MAX_SECONDS < durasi <= SHORTS_URL_CHECK_MAX -> konfirmasi via URL /shorts/.
# - durasi > SHORTS_URL_CHECK_MAX -> pasti bukan Short (Shorts maks 3 menit).
SHORTS_MAX_SECONDS = 60
SHORTS_URL_CHECK_MAX = 180

SKIP_KEYWORDS = [
    # kompilasi / gabungan
    "kompilasi", "kumpulan", "compilation", "playlist", "full episode",
    "full eps", "all episode", "semua episode", "marathon", "non stop",
    "nonstop", "non-stop", "back to back", "rangkuman", "gabungan",
    "sekaligus", "best of", "terlengkap", "pengantar tidur", "sepanjang",
    "2 in 1", "3 in 1", "4 in 1", "5 in 1", "6 in 1", "7 in 1",
    "8 in 1", "9 in 1", "10 in 1", "stream", "streaming",
    # musik / lagu
    "lagu", "lagu anak", "nyanyian", "song", "songs", "full album",
    "album", "medley", "mix", "soundtrack", "ost", "music", "musik",
    "karaoke", "instrumental", "cover", "lirik", "lyric", "remix",
    # non-cerita
    "trailer", "teaser", "cuplikan", "behind the scene", "review",
    "reaction", "reaksi", "vlog", "podcast", "live", "siaran langsung",
    "unboxing", "tutorial", "asmr", "white noise",
    "baju", "kostum", "fashion", "makeup", "tips", "trik", "pakaian",
]

_MULTI_STORY_RE = re.compile(
    r"\b(\d+)\s*(cerita|dongeng|kisah|legenda|fabel|episode|eps)\b",
    re.IGNORECASE,
)


def looks_like_skip(title: str | None) -> str | bool:
    """
    Pra-saring berbasis keyword dan regex (gratis, tanpa kuota API/LLM).
    Mengembalikan keyword string jika cocok, atau False jika lolos.
    """
    if not title:
        return False
    # 1. Pola angka + satuan cerita (mis. "3 Dongeng")
    m = _MULTI_STORY_RE.search(title)
    if m and int(m.group(1)) >= 2:
        return f"multi:{m.group(0).strip()}"

    # 2. Keyword biasa (whole-word)
    t = title.lower()
    for kw in SKIP_KEYWORDS:
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", t):
            return kw
    return False


def _parse_iso8601_duration(s: str | None) -> int:
    """Mengubah format ISO8601 seperti 'PT1H2M3S' menjadi total detik."""
    if not s:
        return 0
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", s)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    mi = int(m.group(2) or 0)
    se = int(m.group(3) or 0)
    return h * 3600 + mi * 60 + se


def is_short_video(video_id: str, duration_seconds: int = 0) -> bool:
    """
    Deteksi apakah video adalah YouTube Shorts:
    1. Durasi <= 60s -> Pasti Short.
    2. Durasi > 180s -> Pasti bukan Short.
    3. 61s-180s atau durasi tidak diketahui -> Verifikasi HEAD ke /shorts/{id}.
    """
    if duration_seconds and duration_seconds <= SHORTS_MAX_SECONDS:
        return True
    if duration_seconds and duration_seconds > SHORTS_URL_CHECK_MAX:
        return False

    try:
        url = f"https://www.youtube.com/shorts/{video_id}"
        with httpx.Client(timeout=5.0, follow_redirects=False) as client:
            resp = client.head(url)
            return resp.status_code == 200
    except Exception:
        return False


def get_best_youtube_bg(video_id: str) -> str:
    """Ambil URL gambar latar YouTube terbaik (maxresdefault dengan fallback hqdefault)."""
    maxres_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.head(maxres_url)
            if resp.status_code == 200:
                return maxres_url
    except Exception:
        pass
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def get_videos_metadata_batch(video_ids: list[str]) -> dict[str, dict[str, Any]]:
    """
    Ambil metadata hingga 50 video per request (Hemat kuota API).
    Return: {video_id: {title, description, channel_id, channel_title, duration_seconds}}
    """
    out = {}
    api_key = settings.YOUTUBE_API_KEY
    if not api_key or not video_ids:
        logger.warning("YOUTUBE_API_KEY belum diset atau daftar video_ids kosong.")
        return out

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        params = {
            "part": "snippet,contentDetails",
            "id": ",".join(chunk),
            "key": api_key,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(f"{YT_API}/videos", params=params)
                if res.status_code != 200:
                    logger.warning(f"Batch metadata API returned status {res.status_code}: {res.text[:150]}")
                    continue
                data = res.json()
        except Exception as exc:
            logger.warning(f"Batch metadata request gagal: {exc}")
            continue

        for item in data.get("items", []):
            vid = item.get("id")
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            if not vid:
                continue
            out[vid] = {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "duration_seconds": _parse_iso8601_duration(content.get("duration", "")),
            }
    return out


def get_youtube_metadata(video_id: str) -> dict[str, Any] | None:
    """
    Ambil metadata untuk 1 video YouTube.
    Jika YOUTUBE_API_KEY kosong, coba fallback ke oEmbed publik.
    """
    if settings.YOUTUBE_API_KEY:
        batch = get_videos_metadata_batch([video_id])
        if video_id in batch:
            return batch[video_id]

    # Fallback oEmbed jika API Key tidak diset / habis kuota
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(oembed_url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("title", ""),
                    "description": "",
                    "channel_id": "",
                    "channel_title": data.get("author_name", ""),
                    "duration_seconds": 0,
                }
    except Exception as exc:
        logger.warning(f"oEmbed fallback gagal untuk video {video_id}: {exc}")

    return None


def list_channel_videos(
    channel_id: str,
    max_results: int = 10,
    processed: set[str] | None = None,
) -> list[dict[str, str]]:
    """
    Mendapatkan daftar video terbaru dari suatu channel via YouTube Data API (uploads playlist)
    atau fallback ke YouTube RSS Feed jika API Key tidak ada.
    """
    processed = processed or set()
    videos = []
    api_key = settings.YOUTUBE_API_KEY

    # 1. Coba via YouTube Data API v3 jika API Key tersedia
    if api_key:
        try:
            with httpx.Client(timeout=10.0) as client:
                ch = client.get(
                    f"{YT_API}/channels",
                    params={"part": "contentDetails", "id": channel_id, "key": api_key},
                ).json()
            items = ch.get("items", [])
            if items:
                uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
                with httpx.Client(timeout=10.0) as client:
                    pl = client.get(
                        f"{YT_API}/playlistItems",
                        params={
                            "part": "snippet,contentDetails",
                            "playlistId": uploads,
                            "maxResults": min(max_results, 50),
                            "key": api_key,
                        },
                    ).json()
                for it in pl.get("items", []):
                    vid = (it.get("contentDetails") or {}).get("videoId")
                    title = (it.get("snippet") or {}).get("title")
                    if vid and title and vid not in processed:
                        videos.append({"id": vid, "title": title})
                return videos
        except Exception as exc:
            logger.warning(f"Data API channel scan gagal, mencoba RSS fallback: {exc}")

    # 2. Fallback via YouTube RSS XML Feed (Gratis tanpa kuota)
    try:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(rss_url)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
                entries = root.findall("atom:entry", ns)
                for entry in entries:
                    vid_node = entry.find("yt:videoId", ns)
                    title_node = entry.find("atom:title", ns)
                    if vid_node is not None and title_node is not None:
                        vid = vid_node.text
                        title = title_node.text
                        if vid and title and vid not in processed:
                            videos.append({"id": vid, "title": title})
                            if len(videos) >= max_results:
                                break
    except Exception as exc:
        logger.error(f"RSS fallback gagal untuk channel {channel_id}: {exc}")

    return videos

