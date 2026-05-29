#!/usr/bin/env python3
"""Check the configured feeds for posts published since yesterday and email a digest.

For each new post the digest includes the title, link, and a ~2-sentence summary.
If nothing new is found, the email says so.

Configuration (environment variables):
  FEEDS_FILE     Path to the feed list (default: feeds.txt)
  SINCE_HOURS    Look-back window in hours (default: 24)

  SMTP_HOST      SMTP server hostname (required to send)
  SMTP_PORT      SMTP port (default: 587)
  SMTP_USERNAME  SMTP login (optional if the server allows anonymous relay)
  SMTP_PASSWORD  SMTP password / app password / API key
  SMTP_SECURITY  "starttls" (default), "ssl", or "none"
  EMAIL_FROM     From address (default: SMTP_USERNAME)
  EMAIL_TO       Comma-separated recipient list (required to send)
  EMAIL_SUBJECT  Subject prefix (default: "Newsletter digest")

  DRY_RUN        If "1"/"true", print the digest instead of sending email.
"""

from __future__ import annotations

import html
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr

import feedparser


def env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def load_feeds(path: str) -> list[str]:
    if not os.path.exists(path):
        raise SystemExit(f"Feed list not found: {path}")
    feeds: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            feeds.append(line)
    return feeds


def entry_datetime(entry) -> datetime | None:
    """Return a timezone-aware UTC datetime for the entry, or None if unknown."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            # feedparser returns a time.struct_time in UTC.
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def summarize(entry, max_sentences: int = 2) -> str:
    raw = ""
    if entry.get("summary"):
        raw = entry["summary"]
    elif entry.get("content"):
        try:
            raw = entry["content"][0].get("value", "")
        except (IndexError, AttributeError):
            raw = ""
    text = html.unescape(_TAG_RE.sub(" ", raw))
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return "(No summary available.)"
    sentences = _SENTENCE_RE.split(text)
    summary = " ".join(sentences[:max_sentences]).strip()
    if len(sentences) > max_sentences and not summary.endswith(("…", ".", "!", "?")):
        summary += "…"
    return summary


def collect_new_posts(feeds: list[str], cutoff: datetime):
    """Return (posts, errors). posts is a list of dicts sorted newest-first."""
    posts = []
    errors = []
    for url in feeds:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            errors.append(f"{url}: {parsed.get('bozo_exception', 'could not parse feed')}")
            continue
        source = parsed.feed.get("title", url)
        for entry in parsed.entries:
            when = entry_datetime(entry)
            if when is None or when < cutoff:
                continue
            posts.append(
                {
                    "source": source,
                    "title": entry.get("title", "(untitled)").strip(),
                    "link": entry.get("link", "").strip(),
                    "published": when,
                    "summary": summarize(entry),
                }
            )
    posts.sort(key=lambda p: p["published"], reverse=True)
    return posts, errors


def render_text(posts, errors, cutoff: datetime) -> str:
    lines = [f"New posts published since {cutoff:%Y-%m-%d %H:%M UTC}", ""]
    if not posts:
        lines.append("Nothing new since yesterday.")
    else:
        for p in posts:
            lines.append(f"• {p['title']}  ({p['source']})")
            if p["link"]:
                lines.append(f"  {p['link']}")
            lines.append(f"  {p['published']:%Y-%m-%d %H:%M UTC}")
            lines.append(f"  {p['summary']}")
            lines.append("")
    if errors:
        lines.append("")
        lines.append("Feeds that could not be read:")
        lines.extend(f"  - {e}" for e in errors)
    return "\n".join(lines).rstrip() + "\n"


def render_html(posts, errors, cutoff: datetime) -> str:
    parts = [
        "<html><body style=\"font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.5;color:#1a1a1a;\">",
        f"<p style=\"color:#666;\">New posts published since {html.escape(f'{cutoff:%Y-%m-%d %H:%M UTC}')}</p>",
    ]
    if not posts:
        parts.append("<p><strong>Nothing new since yesterday.</strong></p>")
    else:
        for p in posts:
            title = html.escape(p["title"])
            source = html.escape(p["source"])
            link = html.escape(p["link"])
            summary = html.escape(p["summary"])
            when = html.escape(f"{p['published']:%Y-%m-%d %H:%M UTC}")
            heading = f"<a href=\"{link}\">{title}</a>" if link else title
            parts.append(
                "<div style=\"margin:0 0 20px;\">"
                f"<div style=\"font-size:16px;font-weight:600;\">{heading}</div>"
                f"<div style=\"color:#888;font-size:12px;\">{source} · {when}</div>"
                f"<div style=\"margin-top:4px;\">{summary}</div>"
                "</div>"
            )
    if errors:
        items = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
        parts.append(
            f"<hr><p style=\"color:#b00;font-size:12px;\">Feeds that could not be read:<ul>{items}</ul></p>"
        )
    parts.append("</body></html>")
    return "".join(parts)


def send_email(subject: str, text_body: str, html_body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    to = os.environ.get("EMAIL_TO", "").strip()
    if not host or not to:
        raise SystemExit(
            "SMTP_HOST and EMAIL_TO must be set to send email "
            "(or set DRY_RUN=1 to print instead)."
        )
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    security = os.environ.get("SMTP_SECURITY", "starttls").strip().lower()
    sender = os.environ.get("EMAIL_FROM") or username
    if not sender:
        raise SystemExit("EMAIL_FROM or SMTP_USERNAME must be set as the sender address.")
    recipients = [addr.strip() for addr in to.split(",") if addr.strip()]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Newsletter", sender))
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            if username and password:
                server.login(username, password)
            server.send_message(msg, to_addrs=recipients)
    else:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            if security == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if username and password:
                server.login(username, password)
            server.send_message(msg, to_addrs=recipients)


def main() -> int:
    feeds_file = os.environ.get("FEEDS_FILE", "feeds.txt")
    since_hours = float(os.environ.get("SINCE_HOURS", "24"))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    feeds = load_feeds(feeds_file)
    if not feeds:
        raise SystemExit(
            f"No feeds configured in {feeds_file}. Add feed URLs (uncomment/replace the placeholders)."
        )

    posts, errors = collect_new_posts(feeds, cutoff)
    text_body = render_text(posts, errors, cutoff)
    html_body = render_html(posts, errors, cutoff)

    count = len(posts)
    prefix = os.environ.get("EMAIL_SUBJECT", "Newsletter digest")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subject = f"{prefix} — {today} ({count} new)" if count else f"{prefix} — {today} (nothing new)"

    if env_bool("DRY_RUN"):
        print(f"Subject: {subject}\n")
        print(text_body)
        if errors:
            return 0
        return 0

    send_email(subject, text_body, html_body)
    print(f"Sent digest: {subject}")
    if errors:
        print(f"Note: {len(errors)} feed(s) failed to load.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
