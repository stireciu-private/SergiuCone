"""Pagina HTML a raportului. Stiluri inline, pe o coloană, ca să arate bine și în e-mail pe telefon."""

import re
from collections import defaultdict
from datetime import datetime
from html import escape

from .fetch import Article, SiteResult

ZILE = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
        "august", "septembrie", "octombrie", "noiembrie", "decembrie"]

FONT = "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif"


def source_name(site: str) -> str:
    """'https://www.ft.com/' -> 'ft.com'; păstrează calea dacă există ('home.barclays/news/press-releases')."""
    name = site.split("://", 1)[-1].removeprefix("www.").rstrip("/")
    return name.removesuffix("/index.html")


def failure_reason(result: SiteResult) -> str:
    """Motivul, pe înțelesul cititorului, pentru care de pe un site nu s-a cules nimic."""
    error = result.error
    code = re.match(r"(\d{3}) ", error)
    if code:
        status = int(code.group(1))
        if status in (401, 403):
            return f"Site-ul blochează accesul automat ({status})"
        if status == 402:
            return "Conținut doar cu abonament (402)"
        if status == 404:
            return "Pagina nu mai există (404)"
        if status == 429:
            return "Site-ul a limitat accesul, prea multe cereri (429)"
        if status >= 500:
            return f"Site-ul are probleme tehnice ({status})"
        return f"Site-ul a refuzat cererea ({status})"
    if "NameResolution" in error or "getaddrinfo" in error:
        return "Adresa nu există sau domeniul a expirat"
    if "timed out" in error.lower():
        return "Site-ul nu a răspuns la timp"
    if "SSL" in error or "certificate" in error.lower():
        return "Problemă cu certificatul de securitate al site-ului"
    if "Connection" in error:
        return "Nu se poate face conexiunea cu site-ul"
    if not error or "nu am găsit" in error:
        return "Site-ul răspunde, dar pagina nu conține titluri de articole (nici flux RSS)"
    return f"Eroare: {error[:80]}"


def count(n: int, singular: str, plural: str) -> str:
    """Numărul cu substantivul acordat: 1 site, 5 site-uri, 21 de site-uri, 236 de site-uri."""
    if n == 1:
        return f"1 {singular}"
    return f"{n} de {plural}" if n % 100 >= 20 or (n and n % 100 == 0) else f"{n} {plural}"


def romanian_date(dt: datetime) -> str:
    return f"{ZILE[dt.weekday()]}, {dt.day} {LUNI[dt.month - 1]} {dt.year}"


def _article_html(article: Article, keywords: list[str]) -> str:
    tags = " ".join(
        f'<span style="display:inline-block;background:#e8eef7;color:#1d4e89;border-radius:3px;'
        f'padding:1px 6px;margin:2px 2px 0 0;font-size:12px">{escape(k.rstrip("*"))}</span>'
        for k in keywords
    )
    summary = (
        f'<div style="color:#555;font-size:14px;margin-top:4px">{escape(article.summary)}</div>'
        if article.summary else ""
    )
    time = (
        f'<span style="color:#888;font-size:12px">{article.published.astimezone():%H:%M}</span> '
        if article.published else ""
    )
    return (
        '<div style="padding:10px 0;border-bottom:1px solid #eee">'
        f'<a href="{escape(article.url)}" style="color:#0b57d0;font-size:16px;font-weight:600;'
        f'text-decoration:none;line-height:1.35">{escape(article.title)}</a>'
        f"{summary}<div style=\"margin-top:4px\">{time}{tags}</div></div>"
    )


def build_report(
    matches: list[tuple[Article, list[str]]],
    results: list[SiteResult],
    now: datetime,
) -> str:
    by_source: dict[str, list] = defaultdict(list)
    for article, keywords in matches:
        by_source[article.source].append((article, keywords))

    sections = []
    for source in sorted(by_source):
        items = sorted(
            by_source[source],
            key=lambda m: m[0].published.timestamp() if m[0].published else 0,
            reverse=True,
        )
        sections.append(
            f'<h2 style="font-size:15px;color:#333;margin:24px 0 0;padding-bottom:4px;'
            f'border-bottom:2px solid #1d4e89">{escape(source)} '
            f'<span style="color:#888;font-weight:normal">({len(items)})</span></h2>'
            + "".join(_article_html(a, k) for a, k in items)
        )

    if not sections:
        sections.append('<p style="color:#555">Niciun articol nou de ieri încoace.</p>')

    failed = [r for r in results if r.error or not r.articles]
    cell = "padding:5px 8px;border-top:1px solid #f0dcb4;vertical-align:top"
    failed_table = (
        '<div style="background:#fdf3e1;color:#7a4b00;font-size:13px;line-height:1.4;padding:8px 10px;'
        'border-radius:4px;margin:12px 0 0">'
        f"<b>Site-uri de pe care nu s-a putut culege nimic ({len(failed)})</b>"
        '<table role="presentation" style="width:100%;border-collapse:collapse;margin-top:6px;font-size:13px">'
        f'<tr><th style="{cell};text-align:left;border-top:none">Site</th>'
        f'<th style="{cell};text-align:left;border-top:none">Motiv</th></tr>'
        + "".join(
            f'<tr><td style="{cell};word-break:break-all;width:40%">{escape(source_name(r.site))}</td>'
            f'<td style="{cell}">{escape(failure_reason(r))}</td></tr>'
            for r in failed
        )
        + "</table></div>"
        if failed else ""
    )
    ok = len(results) - len(failed)
    sites_line = f"Am căutat pe {count(len(results), 'site', 'site-uri')}: " + (
        f"{ok} {'a răspuns' if ok == 1 else 'au răspuns'} cu articole, "
        f"iar de pe {len(failed)} nu s-a putut culege nimic (sunt în tabelul de mai jos)."
        if failed else "de pe toate s-au putut culege articole."
    )
    found_line = (
        f"Pe temele urmărite am găsit {count(len(matches), 'articol nou', 'articole noi')}, "
        f"din {count(len(by_source), 'sursă', 'surse')}."
        if matches else "Pe temele urmărite nu am găsit niciun articol nou."
    )
    subtitle = (
        f'<p style="color:#444;font-size:15px;line-height:1.5;margin:6px 0 0">{escape(sites_line)}<br>'
        f"<b>{escape(found_line)}</b></p>"
    )

    title = f"Revista presei – {romanian_date(now)} (creată de Alex)"
    return (
        f'<!doctype html><html lang="ro"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title></head>"
        f'<body style="margin:0;background:#fff;{FONT}">'
        f'<div style="max-width:680px;margin:0 auto;padding:16px">'
        f'<h1 style="font-size:20px;margin:0 0 4px">{escape(title)}</h1>'
        + subtitle
        + failed_table
        + "".join(sections)
        + "</div></body></html>"
    )
