"""Memoria între rulări: ce articole au fost deja trimise și când a plecat ultimul e-mail."""

import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

KEEP_DAYS = 90


def canonical_url(url: str) -> str:
    """Scoate parametrii de tracking (utm_*, fbclid...) ca același articol să nu apară de două ori."""
    parts = urlparse(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    ]
    return urlunparse(parts._replace(query=urlencode(query), fragment="", netloc=parts.netloc.lower()))


class State:
    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.seen: dict[str, str] = data.get("seen", {})
        self.last_sent: str | None = data.get("last_sent")

    def is_new(self, url: str) -> bool:
        return canonical_url(url) not in self.seen

    def mark_seen(self, urls: list[str], today: date) -> None:
        for url in urls:
            self.seen.setdefault(canonical_url(url), today.isoformat())

    def save(self, today: date) -> None:
        cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
        self.seen = {u: d for u, d in self.seen.items() if d >= cutoff}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"last_sent": self.last_sent, "seen": dict(sorted(self.seen.items()))}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
