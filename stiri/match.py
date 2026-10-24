"""Potrivirea subiectelor din config/keywords.txt cu titlul și rezumatul articolelor.

Fiecare rând din fișier e un subiect, cu variante despărțite prin " | ", de obicei în engleză și în română.
Un articol se potrivește cu subiectul dacă una dintre variante apare în text:
- cuvintele se compară după rădăcină (română și engleză): „plăți” = „plata” = „plățile”, „payments” = „payment”;
- majusculele și diacriticele nu contează, cu excepția acronimelor (vezi mai jos);
- cuvintele unei expresii trebuie să apară în aceeași ordine, cu cel mult MAX_GAP cuvinte între ele;
- cuvintele mărunte (in, of, by, de, la, cu...) din expresii sunt ignorate;
- un * la final prinde orice terminație: „înșelăt*” găsește înșelătorie, înșelătorii, înșelați;
- o variantă între ghilimele („"pay by bank"”) trebuie să apară exact, cuvânt cu cuvânt, cu tot cu cuvintele mărunte;
- acronimele (cel puțin două majuscule sau cifre: AML, MiCA, DORA, PSD2, A2A) se caută exact așa cum sunt
  scrise, ca „MiCA” să nu prindă „mică”, iar „DORA” să nu prindă numele „Dora”. Pluralul cu -s e acceptat.
"""

import re
import unicodedata
from functools import lru_cache

import snowballstemmer

MAX_GAP = 3
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "by", "to", "for", "and", "with",
    "de", "la", "cu", "si", "al", "ai", "ale", "pe", "pentru", "din", "prin", "ce",
}
TOKEN = re.compile(r"\w+")

_ro = snowballstemmer.stemmer("romanian")
_en = snowballstemmer.stemmer("english")


def normalize(text: str) -> str:
    """'Băncile ȘI dobânzile' -> 'bancile si dobanzile' (merge și pentru ş/ţ cu sedilă)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@lru_cache(maxsize=100_000)
def stems(norm_word: str) -> frozenset[str]:
    ro = _ro.stemWord(norm_word)
    result = {norm_word, ro, _en.stemWord(norm_word)}
    if ro.endswith("ur") and len(ro) > 4:  # pluralul românesc în -uri: carduri -> card, atacuri -> atac
        result.add(ro[:-2])
    return frozenset(result)


def _is_acronym(word: str) -> bool:
    return sum(c.isupper() or c.isdigit() for c in word) >= 2


class _Word:
    def __init__(self, raw: str):
        self.raw = raw
        self.acronym = _is_acronym(raw)
        self.prefix = raw.endswith("*")
        self.norm = normalize(raw.rstrip("*"))
        self.stems = stems(self.norm)

    def matches(self, original: str, norm: str) -> bool:
        if self.acronym:
            return original.removesuffix("s") == self.raw.removesuffix("s")
        if self.prefix:
            return norm.startswith(self.norm)
        return not self.stems.isdisjoint(stems(norm))


def _parse_variant(text: str) -> tuple[list[_Word], int]:
    """Cuvintele variantei și distanța maximă dintre ele. Între ghilimele: expresie exactă, cuvânt cu cuvânt."""
    exact = len(text) > 1 and text[0] == text[-1] == '"'
    raw_words = re.findall(r"[\w*]+", text)
    if exact:
        return [_Word(w) for w in raw_words], 0
    words = [_Word(w) for w in raw_words if _is_acronym(w) or normalize(w) not in STOPWORDS]
    return words or [_Word(w) for w in raw_words], MAX_GAP


class KeywordMatcher:
    def __init__(self, lines: list[str]):
        self.topics: list[tuple[str, list[tuple[list[_Word], int]]]] = []
        for line in lines:
            variants = [v.strip() for v in line.split("|") if v.strip()]
            parsed = [p for p in (_parse_variant(v) for v in variants) if p[0]]
            if parsed:
                self.topics.append((variants[0].strip('"'), parsed))

    def find(self, text: str) -> list[str]:
        """Numele subiectelor (prima variantă de pe rând) găsite în text."""
        tokens = [(t, normalize(t)) for t in TOKEN.findall(text)]
        return [
            name for name, variants in self.topics
            if any(_occurs(words, gap, tokens) for words, gap in variants)
        ]


def _occurs(words: list[_Word], gap: int, tokens: list[tuple[str, str]]) -> bool:
    def from_pos(word_index: int, start: int, limit: int) -> bool:
        if word_index == len(words):
            return True
        for pos in range(start, min(limit, len(tokens))):
            if words[word_index].matches(*tokens[pos]) and from_pos(word_index + 1, pos + 1, pos + 2 + gap):
                return True
        return False

    return from_pos(0, 0, len(tokens))
