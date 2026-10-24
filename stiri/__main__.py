"""Rularea zilnică: descarcă, filtrează, trimite fiecărui destinatar articolele pe care nu le-a mai primit.

    python -m stiri              rulează acum și trimite e-mailurile (câte unul pentru fiecare adresă din MAIL_TO)
    python -m stiri --dry-run    doar salvează în reports/ pagina cu toate articolele găsite, adică ce ar
                                 primi un destinatar nou; fără e-mail, fără să modifice memoria
    python -m stiri --scheduled  folosit de GitHub Actions: trimite doar după 8:00 ora României și doar
                                 destinatarilor care n-au primit încă e-mailul azi
"""

import argparse
import logging
import os
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
MAX_AGE = timedelta(days=3)  # articole RSS mai vechi de atât sunt ignorate (contează pentru destinatarii noi)
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


def masked(email: str) -> str:
    """Pentru jurnale: 'prieten@gmail.com' -> 'p***@gmail.com'."""
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}"


def main() -> int:
    parser = argparse.ArgumentParser(prog="stiri")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--scheduled", action="store_true")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):  # consola Windows nu e UTF-8 implicit
        stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    now = datetime.now(TZ)
    today = now.date()
    state = State(ROOT / "data" / "seen.json")
    recipients = [a.strip() for a in os.environ.get("MAIL_TO", "").split(",") if a.strip()]
    if not recipients and not args.dry_run:
        log.error("MAIL_TO nu conține nicio adresă.")
        return 1

    # GitHub pornește jobul la 05:00 și 06:00 UTC; doar unul dintre ele cade după 8:00 ora României,
    # indiferent de ora de vară/iarnă.
    if args.scheduled:
        recipients = [r for r in recipients if not state.sent_today(r, today)]
        if now.hour < SEND_HOUR or not recipients:
            log.info("Nu e momentul trimiterii (ora %s, destinatari în așteptare: %d).",
                     now.strftime("%H:%M"), len(recipients))
            return 0

    sites = read_list(ROOT / "config" / "sites.txt")
    matcher = KeywordMatcher(read_list(ROOT / "config" / "keywords.txt"))

    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(fetch_site, sites))
    for r in results:
        log.info("%-40s %-7s %4d articole %s", r.site, r.method or "-", len(r.articles), r.error)

    candidates, seen_urls, seen_titles = [], set(), set()
    for result in results:
        for article in result.articles:
            if article.published and now - article.published > MAX_AGE:
                continue
            url, title_key = canonical_url(article.url), normalize(article.title)
            if url in seen_urls or title_key in seen_titles:
                continue
            keywords = matcher.find(f"{article.title} {article.summary}")
            if keywords:
                seen_urls.add(url)
                seen_titles.add(title_key)
                candidates.append((article, keywords))

    path = report_path(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_report(candidates, results, now), encoding="utf-8")
    log.info("%d articole găsite -> %s", len(candidates), path.relative_to(ROOT))

    if args.dry_run:
        return 0

    failures = 0
    for recipient in recipients:
        new = [(a, k) for a, k in candidates if state.is_new(recipient, a.url)]
        html = build_report(new, results, now)
        subject = f"Revista presei – {romanian_date(now)} ({len(new)} articole noi)"
        try:
            send_report(subject, html, recipient, f"stiri_{now:%Y-%m-%d}.html")
        except Exception:
            log.exception("Trimiterea către %s a eșuat.", masked(recipient))
            failures += 1
            continue
        state.mark_sent(recipient, [a.url for a, _ in new], today)
        state.save(today)  # după fiecare trimitere reușită, ca o eroare ulterioară să nu provoace retrimiteri
        log.info("E-mail trimis către %s: %d articole noi.", masked(recipient), len(new))

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
