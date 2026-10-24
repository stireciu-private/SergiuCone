"""Potrivirea cuvintelor-cheie, fără să conteze majusculele și diacriticele."""

import re
import unicodedata


def normalize(text: str) -> str:
    """'Băncile ȘI dobânzile' -> 'bancile si dobanzile' (merge și pentru ş/ţ cu sedilă)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


class KeywordMatcher:
    def __init__(self, keywords: list[str]):
        self.patterns = []
        for kw in keywords:
            prefix = kw.endswith("*")
            body = normalize(kw.rstrip("*").strip())
            if not body:
                continue
            escaped = r"\s+".join(re.escape(part) for part in body.split())
            pattern = rf"(?<!\w){escaped}{r'\w*' if prefix else ''}(?!\w)"
            self.patterns.append((kw, re.compile(pattern)))

    def find(self, text: str) -> list[str]:
        norm = normalize(text)
        return [kw for kw, pattern in self.patterns if pattern.search(norm)]
