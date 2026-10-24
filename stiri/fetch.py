"""Descărcarea articolelor: întâi RSS, iar dacă site-ul nu are, titlurile din pagina principală."""

import calendar
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept-Language": "ro,en;q=0.8",
}
TIMEOUT = 20
COMMON_FEED_PATHS = ("/feed/", "/rss", "/rss.xml", "/feed.xml")
MIN_HEADLINE_LENGTH = 30


@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str = ""
    published: datetime | None = None


@dataclass
class SiteResult:
    site: str
    articles: list[Article]
    method: str = ""  # "rss" sau "pagină"
    error: str = ""


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def _looks_like_feed(resp: requests.Response) -> bool:
    ctype = resp.headers.get("Content-Type", "").lower()
    if "xml" in ctype or "rss" in ctype or "atom" in ctype:
        return True
    head = resp.content[:500].lstrip().lower()
    return head.startswith((b"<?xml", b"<rss", b"<feed"))


def _clean_text(html: str, limit: int = 300) -> str:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _parse_feed(content: bytes, source: str) -> list[Article]:
    feed = feedparser.parse(content)
    articles = []
    for entry in feed.entries:
        title = _clean_text(entry.get("title", ""), limit=500)
        link = entry.get("link", "")
        if not title or not link:
            continue
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = (
            datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc) if parsed else None
        )
        articles.append(
            Article(title, link, source, _clean_text(entry.get("summary", "")), published)
        )
    return articles


def _feed_links(soup: BeautifulSoup, base: str) -> list[str]:
    links = []
    for tag in soup.find_all("link", rel="alternate"):
        ctype = (tag.get("type") or "").lower()
        if ("rss" in ctype or "atom" in ctype) and tag.get("href"):
            links.append(urljoin(base, tag["href"]))
    root = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    links.extend(root + path for path in COMMON_FEED_PATHS)
    return list(dict.fromkeys(links))


def _scrape_headlines(soup: BeautifulSoup, base: str, source: str) -> list[Article]:
    domain = urlparse(base).netloc.removeprefix("www.")
    seen, articles = set(), []
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        url = urljoin(base, a["href"]).split("#")[0]
        if len(title) < MIN_HEADLINE_LENGTH or url in seen:
            continue
        if urlparse(url).netloc.removeprefix("www.") != domain:
            continue
        seen.add(url)
        articles.append(Article(title, url, source))
    return articles


def fetch_site(site: str) -> SiteResult:
    source = urlparse(site).netloc.removeprefix("www.") or site
    try:
        resp = _get(site)
        if _looks_like_feed(resp):
            return SiteResult(site, _parse_feed(resp.content, source), "rss")

        # Fără charset în antet, requests presupune ISO-8859-1 și strică diacriticele;
        # atunci lăsăm BeautifulSoup să citească <meta charset> din pagină.
        declared = "charset" in resp.headers.get("Content-Type", "").lower()
        soup = BeautifulSoup(resp.content, "html.parser", from_encoding=resp.encoding if declared else None)
        for feed_url in _feed_links(soup, resp.url):
            try:
                feed_resp = _get(feed_url)
            except requests.RequestException:
                continue
            if _looks_like_feed(feed_resp):
                articles = _parse_feed(feed_resp.content, source)
                if articles:
                    return SiteResult(site, articles, "rss")

        articles = _scrape_headlines(soup, resp.url, source)
        if not articles:
            return SiteResult(site, [], "pagină", "nu am găsit nici RSS, nici titluri în pagină")
        return SiteResult(site, articles, "pagină")
    except Exception as exc:  # un site căzut nu trebuie să oprească restul
        log.warning("%s: %s", site, exc)
        return SiteResult(site, [], error=str(exc)[:200])
