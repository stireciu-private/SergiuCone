"""Rularea zilnică: descarcă, filtrează, păstrează doar articolele noi, salvează pagina, trimite e-mailul.

    python -m stiri              rulează acum și trimite e-mailul
    python -m stiri --dry-run    doar salvează pagina (fără e-mail, fără să marcheze articolele ca văzute)
    python -m stiri --scheduled  folosit de GitHub Actions: trimite doar dacă e trecut de 8:00
                                 ora României și nu s-a trimis deja azi
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .fetch import fetch_site
from .mailer import send_report
from .match import KeywordMatcher, normalize
from .report import build_report, romanian_date
from .state import State, canonical_url

ROOT = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Bucharest")
SEND_HOUR = 8
MAX_AGE = timedelta(days=3)  # articole RSS mai vechi de atât sunt ignorate (contează la prima rulare)
WORKERS = 16

log = logging.getLogger("stiri")


def read_list(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def report_path(now: datetime) -> Path:
    path = ROOT / "reports" / f"stiri_{now:%Y-%m-%d}.html"
    if path.exists():
        path = path.with_name(f"stiri_{now:%Y-%m-%d_%H%M}.html")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(prog="stiri")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scheduled", action="store_true")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):  # consola Windows nu e UTF-8 implicit
        stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    now = datetime.now(TZ)
    state = State(ROOT / "data" / "seen.json")

    # GitHub pornește jobul la 05:00 și 06:00 UTC; doar unul dintre ele cade după 8:00 ora României,
    # indiferent de ora de vară/iarnă.
    if args.scheduled and (now.hour < SEND_HOUR or state.last_sent == now.date().isoformat()):
        log.info("Nu e momentul trimiterii (ora %s, ultima trimitere %s).", now.strftime("%H:%M"), state.last_sent)
        return 0

    sites = read_list(ROOT / "config" / "sites.txt")
    matcher = KeywordMatcher(read_list(ROOT / "config" / "keywords.txt"))

    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(fetch_site, sites))
    for r in results:
        log.info("%-40s %-7s %4d articole %s", r.site, r.method or "-", len(r.articles), r.error)

    matches, seen_urls, seen_titles = [], set(), set()
    for result in results:
        for article in result.articles:
            if article.published and now - article.published > MAX_AGE:
                continue
            url, title_key = canonical_url(article.url), normalize(article.title)
            if url in seen_urls or title_key in seen_titles or not state.is_new(url):
                continue
            keywords = matcher.find(f"{article.title} {article.summary}")
            if keywords:
                seen_urls.add(url)
                seen_titles.add(title_key)
                matches.append((article, keywords))

    html = build_report(matches, results, now)
    path = report_path(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    log.info("%d articole noi -> %s", len(matches), path.relative_to(ROOT))

    if args.dry_run:
        return 0

    subject = f"Revista presei – {romanian_date(now)} ({len(matches)} articole noi)"
    send_report(subject, html, path)
    log.info("E-mail trimis.")

    state.mark_seen([a.url for a, _ in matches], now.date())
    state.last_sent = now.date().isoformat()
    state.save(now.date())
    return 0


if __name__ == "__main__":
    sys.exit(main())
