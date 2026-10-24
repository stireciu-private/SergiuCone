# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Daily Romanian press digest for a non-technical user: fetch ~200 finance/banking/geopolitics news sites,
keep articles matching ~300 keywords that were not sent before, email an HTML page. Runs on GitHub Actions
(`.github/workflows/daily.yml`). The user-facing text (README, report, logs, comments) is in Romanian; keep it that way.
Phase 2 (planned, not started): publishing a hand-picked subset on the friend's own website.

## Commands

```
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m stiri --dry-run     # fetch + write reports/stiri_<date>.html with ALL matches (= what a new recipient gets); no email, state untouched
.venv\Scripts\python -m stiri               # also email (needs SMTP_USER, SMTP_PASSWORD, MAIL_TO; SMTP_HOST/PORT default to Gmail 465)
.venv\Scripts\python -m stiri --scheduled   # what cron runs: no-op before 08:00 Europe/Bucharest; sends only to recipients not yet served today
```

There is no test suite yet.

## Architecture (`stiri/`)

- `fetch.py`: per site, in order: the URL itself if it is a feed → `<link rel=alternate>` feeds and common paths
  (`/feed/`, `/rss`...) → fallback scraping same-domain `<a>` texts ≥ 30 chars from the homepage. Scraped items have
  no date. Any exception becomes `SiteResult.error` so one broken site never stops the run; errors are listed at
  the bottom of the report.
- `match.py`: keywords and text are normalized (lowercase, diacritics stripped via NFKD, so ș/ş/s are equal);
  trailing `*` = prefix match; otherwise whole-word.
- `state.py`: `data/seen.json` holds, **per recipient** (keyed by a sha256 prefix of the address, never the address),
  canonical URLs (tracking params stripped) already emailed and `last_sent`. A new address starts empty, so its first
  email has every current match: an explicit user requirement. Each address gets its own email (`MAIL_TO` is comma-separated).
  GitHub Actions has no persistent disk; the workflow carries `seen.json` between runs via `actions/cache`
  (restore by prefix `seen-`, save under a new per-run key). The workflow deliberately makes **no commits**
  (user's choice); `data/` and `reports/` are gitignored. Losing the cache only means one email with repeats.
- `report.py`: one HTML used both as email body and as attachment/archive. All styles must stay **inline**,
  single-column (read mostly on an Android phone in Gmail); keep markup compact because Gmail clips bodies over ~102 KB.
- `__main__.py`: orchestration. State is updated only after the email is sent successfully.

## Gotchas

- Cron is UTC with no DST: two triggers (05:00 and 06:00 UTC) plus the `--scheduled` gate give one send at 08:00 local year-round.
- Pages without a charset in `Content-Type` must be decoded by BeautifulSoup from bytes (requests would assume ISO-8859-1 and garble diacritics).
- RSS items older than `MAX_AGE` (3 days) are dropped, mainly so the first run isn't flooded.
