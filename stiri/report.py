"""Pagina HTML a raportului. Stiluri inline, pe o coloană, ca să arate bine și în e-mail pe telefon."""

from collections import defaultdict
from datetime import datetime
from html import escape

from .fetch import Article, SiteResult

ZILE = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
        "august", "septembrie", "octombrie", "noiembrie", "decembrie"]

FONT = "font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif"


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

    failed = [r for r in results if r.error]
    footer = (
        f'<p style="color:#888;font-size:12px;margin-top:32px">Site-uri verificate: '
        f"{len(results)} · articole noi: {len(matches)}</p>"
    )
    if failed:
        footer += (
            '<details style="color:#888;font-size:12px"><summary>Site-uri care nu au răspuns '
            f"({len(failed)})</summary><ul>"
            + "".join(f"<li>{escape(r.site)}: {escape(r.error)}</li>" for r in failed)
            + "</ul></details>"
        )

    title = f"Revista presei – {romanian_date(now)}"
    return (
        f'<!doctype html><html lang="ro"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title></head>"
        f'<body style="margin:0;background:#fff;{FONT}">'
        f'<div style="max-width:680px;margin:0 auto;padding:16px">'
        f'<h1 style="font-size:20px;margin:0 0 4px">{escape(title)}</h1>'
        f'<p style="color:#555;margin:0">{len(matches)} articole noi din {len(by_source)} surse</p>'
        + "".join(sections)
        + footer
        + "</div></body></html>"
    )
