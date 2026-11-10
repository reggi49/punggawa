#!/usr/bin/env python3
"""
Setup tabel content_rss_sources di PostgreSQL Supabase.
Menyimpan daftar sumber feed RSS media teknologi, gaming, AI, dan IoT
secara terpusat di database agar mudah ditambah, diubah, atau dinonaktifkan.
"""
import logging
import os
import sys

# Ensure root directory in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator.connections import postgres_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SetupRSSSourcesTable")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS content_rss_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    feed_url TEXT UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'technology',
    is_active BOOLEAN DEFAULT TRUE,
    last_scanned_at TIMESTAMPTZ,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rss_sources_cat ON content_rss_sources (category, is_active);
"""

INITIAL_RSS_FEEDS = [
    # 1. Games (Gaming, PC Ports, Retro, Console)
    ("DSOGaming", "https://www.dsogaming.com/feed/", "games"),
    ("GameSpot", "https://www.gamespot.com/feeds/news/", "games"),
    ("Kotaku", "https://kotaku.com/games/feed", "games"),
    ("PC Gamer", "https://www.pcgamer.com/feeds/articletype/news/", "games"),
    ("IGN", "https://feeds.feedburner.com/ign/news", "games"),
    ("Retro Handhelds", "https://retrohandhelds.gg/feed/", "games"),
    ("Retro Dodo", "https://retrododo.com/rss", "games"),

    # 2. Technology & Artificial Intelligence
    ("The Verge Tech", "https://www.theverge.com/rss/tech/index.xml", "technology"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "technology"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed", "technology"),
    ("Wired Security", "https://www.wired.com/feed/category/security/latest/rss", "technology"),
    ("Wired Science", "https://www.wired.com/feed/category/science/latest/rss", "technology"),
    ("Engadget", "https://www.engadget.com/rss.xml", "technology"),
    ("Tom's Hardware", "https://www.tomshardware.com/feeds.xml", "technology"),
    ("TechPowerUp Reviews", "https://www.techpowerup.com/rss/reviews", "technology"),
    ("IEEE Semiconductors", "https://spectrum.ieee.org/feeds/topic/semiconductors.rss", "technology"),
    ("Guru3D", "https://www.guru3d.com/rss.xml", "technology"),
    ("The Robot Report", "https://www.therobotreport.com/feed/", "technology"),

    # 3. Programming & Open-Source Tech
    ("Hacker News", "https://news.ycombinator.com/rss", "programming"),
    ("IEEE Computing", "https://spectrum.ieee.org/feeds/topic/computing.rss", "programming"),
    ("Phoronix Linux", "https://www.phoronix.com/rss.php", "programming"),
    ("IEEE Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss", "programming"),

    # 4. Internet of Things (Hardware, Maker, DIY)
    ("Hackaday", "https://hackaday.com/feed/", "internet of things"),
    ("CNX Software Embedded", "https://www.cnx-software.com/feed", "internet of things"),
    ("Adafruit Blog", "https://blog.adafruit.com/feed/", "internet of things"),
    ("Arduino Blog", "https://blog.arduino.cc/feed/", "internet of things"),
    ("All About Circuits", "https://www.allaboutcircuits.com/rss/news/", "internet of things"),
    ("Electronics Weekly", "https://www.electronicsweekly.com/feed/", "internet of things"),
]


def setup_rss_sources_table():
    """Membuat tabel content_rss_sources dan meng-insert 28 feed inisial."""
    logger.info("Memulai inisialisasi tabel 'content_rss_sources' di Supabase...")
    try:
        with postgres_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
                logger.info("✅ Tabel 'content_rss_sources' dan index berhasil dibuat.")

                # Insert data inisial (ON CONFLICT DO NOTHING agar idempotent)
                insert_sql = """
                INSERT INTO content_rss_sources (name, feed_url, category)
                VALUES (%s, %s, %s)
                ON CONFLICT (feed_url) DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category;
                """
                for name, url, category in INITIAL_RSS_FEEDS:
                    cur.execute(insert_sql, (name, url, category))

                # Ambil ringkasan sumber per kategori
                cur.execute("""
                    SELECT category, COUNT(*) 
                    FROM content_rss_sources 
                    WHERE is_active = TRUE 
                    GROUP BY category 
                    ORDER BY category;
                """)
                rows = cur.fetchall()
                logger.info("📊 Ringkasan Feed RSS Aktif di Database:")
                total = 0
                for cat, count in rows:
                    total += count
                    logger.info(f"   • {cat:20} : {count} sumber")
                logger.info(f"Total sumber feed terdaftar: {total}")
        return True
    except Exception as exc:
        logger.error(f"❌ Gagal inisialisasi tabel content_rss_sources: {exc}", exc_info=True)
        return False
    finally:
        try:
            postgres_pool.close()
        except Exception:
            pass


if __name__ == "__main__":
    success = setup_rss_sources_table()
    os._exit(0 if success else 1)
