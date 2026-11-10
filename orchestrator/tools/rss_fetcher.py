"""
RSS Feed Fetcher & Parser for Multi-Category Article Curation.
Mendukung penarikan berita real-time dari 28+ sumber media teknologi, gaming,
AI, dan IoT yang tersimpan di PostgreSQL Supabase (content_rss_sources).
"""
import logging
import os
import random
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

from orchestrator.connections import postgres_pool
from orchestrator.tools.base import register_tool

logger = logging.getLogger("RSSFetcher")

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def get_active_rss_sources(category: str | None = None) -> list[dict[str, Any]]:
    """Mengambil daftar sumber RSS aktif dari Supabase PostgreSQL."""
    sql = "SELECT id, name, feed_url, category FROM content_rss_sources WHERE is_active = TRUE"
    params = []
    if category:
        sql += " AND category = %s"
        params.append(category)
    sql += " ORDER BY last_scanned_at ASC NULLS FIRST, id ASC;"

    sources = []
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                for r in rows:
                    sources.append({
                        "id": r[0],
                        "name": r[1],
                        "feed_url": r[2],
                        "category": r[3],
                    })
    except Exception as exc:
        logger.error(f"❌ Gagal mengambil sumber RSS dari database: {exc}")

    return sources


def parse_feed_content(xml_bytes: bytes, source_name: str, category: str) -> list[dict[str, Any]]:
    """Mem-parse payload XML feed (RSS 2.0 atau Atom) menjadi daftar artikel terstandarisasi."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        logger.warning(f"Gagal mem-parse XML untuk {source_name}: {exc}")
        return []

    # Coba format RSS 2.0 (<channel><item>...)
    rss_items = root.findall(".//item")
    if rss_items:
        for entry in rss_items:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            # Beberapa RSS menyimpan URL di <guid isPermaLink="true">
            if not link:
                guid = entry.find("guid")
                if guid is not None and guid.get("isPermaLink", "").lower() == "true":
                    link = (guid.text or "").strip()

            pub_date = (entry.findtext("pubDate") or "").strip()
            desc = (entry.findtext("description") or "").strip()
            # Bersihkan tag HTML sederhana dari deskripsi
            clean_desc = re.sub(r"<[^>]+>", "", desc).strip()

            if title and link:
                items.append({
                    "title": title,
                    "url": link,
                    "published_at": pub_date,
                    "source": source_name,
                    "category": category,
                    "summary": clean_desc[:300],
                })
        return items

    # Coba format Atom (<feed><entry>...)
    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    atom_entries = root.findall(".//atom:entry", atom_ns) or root.findall(".//entry")
    for entry in atom_entries:
        title = (entry.findtext("atom:title", namespaces=atom_ns) or entry.findtext("title") or "").strip()
        link = ""
        link_elem = entry.find("atom:link[@rel='alternate']", atom_ns) or entry.find("link")
        if link_elem is not None:
            link = link_elem.get("href", "").strip()
        if not link:
            link = (entry.findtext("atom:id", namespaces=atom_ns) or entry.findtext("id") or "").strip()

        pub_date = (entry.findtext("atom:published", namespaces=atom_ns) or entry.findtext("published") or entry.findtext("updated") or "").strip()
        summary = (entry.findtext("atom:summary", namespaces=atom_ns) or entry.findtext("summary") or "").strip()
        clean_summary = re.sub(r"<[^>]+>", "", summary).strip()

        if title and link and link.startswith("http"):
            items.append({
                "title": title,
                "url": link,
                "published_at": pub_date,
                "source": source_name,
                "category": category,
                "summary": clean_summary[:300],
            })

    return items


def fetch_articles_from_feed(source: dict[str, Any], timeout: float = 12.0) -> list[dict[str, Any]]:
    """Mengunduh dan mem-parse satu feed RSS/Atom."""
    feed_url = source["feed_url"]
    source_name = source["name"]
    category = source["category"]

    try:
        res = requests.get(feed_url, headers=REQUEST_HEADERS, timeout=timeout)
        if res.status_code != 200:
            logger.warning(f"⚠️ Feed {source_name} merespons status {res.status_code}")
            return []

        items = parse_feed_content(res.content, source_name, category)
        # Update last_scanned_at di database
        try:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE content_rss_sources SET last_scanned_at = NOW(), error_count = 0 WHERE id = %s;",
                        (source["id"],),
                    )
        except Exception:
            pass

        return items
    except Exception as exc:
        logger.warning(f"Gagal mengambil feed {source_name} ({feed_url}): {exc}")
        try:
            with postgres_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE content_rss_sources SET error_count = error_count + 1 WHERE id = %s;",
                        (source["id"],),
                    )
        except Exception:
            pass
        return []


def fetch_next_rss_candidate(
    existing_topics: set[str],
    preferred_category: str | None = None,
) -> tuple[str, str, dict[str, Any]] | None:
    """
    Mengambil 1 artikel berita terbaru dari database RSS sources yang belum pernah ditulis.
    Mendukung filter preferred_category (misal 'games' di slot sore, 'programming'/'technology' di slot pagi).
    """
    sources = get_active_rss_sources(category=preferred_category)
    if not sources and preferred_category:
        # Fallback ke seluruh kategori jika kategori preferensi kosong
        sources = get_active_rss_sources(category=None)

    if not sources:
        return None

    # Acak sedikit urutan sumber dalam kategori agar tidak monoton dari 1 situs saja
    random.shuffle(sources)

    for src in sources[:8]:  # Cek hingga 8 feed
        articles = fetch_articles_from_feed(src)
        for art in articles:
            t = art["title"].strip()
            u = art["url"].strip()
            t_key = t.lower()
            u_key = u.lower()

            if t_key not in existing_topics and u_key not in existing_topics:
                existing_topics.add(t_key)
                existing_topics.add(u_key)

                input_data = {
                    "query": art.get("summary") or t,
                    "topic": t,
                    "task_type": "article",
                    "action": "trend-article",
                    "source": "rss",
                    "target_urls": u,
                    "category": art.get("category", "technology"),
                    "dry_run": False,
                }
                logger.info(
                    f"✨ [RSS Curation] Menemukan artikel baru dari {art['source']} "
                    f"[{art['category']}]: '{t}' ({u})"
                )
                return t, "trend-article", input_data

    return None


@register_tool(
    name="get_rss_feed_topics",
    description="Mengambil artikel berita teknologi, game, AI, atau IoT terbaru dari database feed RSS terdaftar.",
    sensitive=False,
)
def get_rss_feed_topics(category: str = "", max_items: int = 5) -> list[dict[str, Any]]:
    """Tool LangGraph untuk mencari inspirasi artikel dari RSS feed."""
    sources = get_active_rss_sources(category=category or None)
    results = []
    for src in sources[:3]:
        arts = fetch_articles_from_feed(src)
        results.extend(arts)
        if len(results) >= max_items:
            break
    return results[:max_items]
