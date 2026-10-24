"""Memoria între rulări, separată pe destinatar: ce articole i-au fost trimise și când a primit ultimul e-mail.

Un destinatar nou nu are memorie, deci primul lui e-mail conține toate articolele găsite în acel moment.
Adresele nu se salvează în clar, doar un hash al lor.
"""

import hashlib
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


def recipient_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:16]


class State:
    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        # Formatul vechi (o singură memorie comună) e ignorat intenționat: nu se poate ști cărei adrese
        # îi aparținea, iar un destinatar nou trebuie să primească toate articolele.
        self.recipients: dict[str, dict] = data.get("recipients", {})

    def _entry(self, email: str) -> dict:
        return self.recipients.setdefault(recipient_key(email), {"last_sent": None, "seen": {}})

    def is_new(self, email: str, url: str) -> bool:
        return canonical_url(url) not in self._entry(email)["seen"]

    def sent_today(self, email: str, today: date) -> bool:
        return self._entry(email)["last_sent"] == today.isoformat()

    def mark_sent(self, email: str, urls: list[str], today: date) -> None:
        entry = self._entry(email)
        for url in urls:
            entry["seen"].setdefault(canonical_url(url), today.isoformat())
        entry["last_sent"] = today.isoformat()

    def save(self, today: date) -> None:
        cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
        for key, entry in list(self.recipients.items()):
            if (entry["last_sent"] or "") < cutoff:  # destinatar care n-a mai primit nimic de 90 de zile
                del self.recipients[key]
                continue
            entry["seen"] = dict(sorted((u, d) for u, d in entry["seen"].items() if d >= cutoff))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"recipients": self.recipients}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
