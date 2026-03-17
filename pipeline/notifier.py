"""
notifier.py — Send a digest summary email via Gmail SMTP.

Required environment variables (set as GitHub Actions secrets):
    NOTIFY_GMAIL_USER      your Gmail address, e.g. you@gmail.com
    NOTIFY_GMAIL_APP_PASS  16-character App Password (not your login password)
    NOTIFY_TO              recipient address (can be the same as NOTIFY_GMAIL_USER)

Gmail App Password setup:
    1. Enable 2-Step Verification on your Google account.
    2. Go to https://myaccount.google.com/apppasswords
    3. Create an app password for "Mail" → copy the 16-char code.
    4. Add it as a GitHub Secret named NOTIFY_GMAIL_APP_PASS.

If any of the three env vars are missing the notifier silently skips,
so local runs and --refilter/--refetch never fail because of missing creds.
"""

import os
import smtplib
import textwrap
from collections import defaultdict
from datetime import date
from email.message import EmailMessage

# ── Types (mirrors what main.py collects) ────────────────────────────────────

class PaperSummary:
    """Lightweight record passed from main → notifier. No Paper dependency."""
    __slots__ = ("title", "url", "authors", "matched_topics")

    def __init__(self, title: str, url: str, authors: list[str],
                 matched_topics: list[str]):
        self.title          = title
        self.url            = url
        self.authors        = authors
        self.matched_topics = matched_topics


class DaySummary:
    __slots__ = ("day", "matched", "total")

    def __init__(self, day: date, matched: list[PaperSummary], total: int):
        self.day     = day
        self.matched = matched   # only matched papers
        self.total   = total     # matched + unmatched


# ── Email builder ─────────────────────────────────────────────────────────────

def _fmt_day(d: date) -> str:
    """'Mar 7' / 'Mar 17' — no leading zero, works on all platforms."""
    return d.strftime("%b ") + str(d.day)


def _fmt_day_long(d: date) -> str:
    """'Tuesday, March 17 2026' — no leading zero, works on all platforms."""
    return d.strftime("%A, %B ") + str(d.day) + d.strftime(" %Y")


def _build_email(summaries: list[DaySummary], site_url: str | None) -> tuple[str, str]:
    """Return (subject, plain-text body)."""

    # Subject: e.g. "arXiv Digest · Mar 17 — 12 matched"
    # Use the most recent day with any matches for the subject line.
    days_with_matches = [s for s in summaries if s.matched]
    if not days_with_matches:
        subject = "arXiv Digest · no new matches today"
        body    = "The pipeline ran but found no matched papers.\n"
        return subject, body

    latest      = days_with_matches[0]
    date_label  = _fmt_day(latest.day)
    total_match = sum(len(s.matched) for s in days_with_matches)
    subject     = f"arXiv Digest · {date_label} — {total_match} matched"

    lines = []

    for summary in days_with_matches:
        lines.append(f"{'─' * 56}")
        lines.append(f"  {_fmt_day_long(summary.day)}  "
                     f"({len(summary.matched)} matched / {summary.total} total)")
        lines.append(f"{'─' * 56}")

        # Group papers by topic for a cleaner layout
        by_topic: dict[str, list[PaperSummary]] = defaultdict(list)
        for p in summary.matched:
            for t in p.matched_topics:
                by_topic[t].append(p)

        for topic, papers in by_topic.items():
            lines.append(f"\n  ▸ {topic}  ({len(papers)} paper{'s' if len(papers) != 1 else ''})\n")
            for p in papers:
                authors_str = ", ".join(p.authors[:3])
                if len(p.authors) > 3:
                    authors_str += " et al."
                # Wrap title to 72 chars, indented
                title_wrapped = textwrap.fill(p.title, width=68,
                                              initial_indent="    • ",
                                              subsequent_indent="      ")
                lines.append(title_wrapped)
                lines.append(f"      {authors_str}")
                lines.append(f"      {p.url}")
                lines.append("")

    if site_url:
        lines.append(f"{'─' * 56}")
        lines.append(f"  View full digest: {site_url}")

    lines.append("")
    body = "\n".join(lines)
    return subject, body


# ── Send ──────────────────────────────────────────────────────────────────────

def send_digest(summaries: list[DaySummary], site_url: str | None = None) -> None:
    """
    Build and send the digest email.
    Silently skips if credentials are not configured.
    """
    gmail_user = os.environ.get("NOTIFY_GMAIL_USER", "").strip()
    app_pass   = os.environ.get("NOTIFY_GMAIL_APP_PASS", "").strip()
    to_addr    = os.environ.get("NOTIFY_TO", "").strip()

    if not all([gmail_user, app_pass, to_addr]):
        print("[notifier] Credentials not set — skipping email notification.")
        return

    subject, body = _build_email(summaries, site_url)

    msg                  = EmailMessage()
    msg["Subject"]       = subject
    msg["From"]          = f"arXiv Digest <{gmail_user}>"
    msg["To"]            = to_addr
    msg.set_content(body)

    try:
        print(f"[notifier] Sending digest to {to_addr}…")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, app_pass)
            smtp.send_message(msg)
        print(f"[notifier] Sent: {subject!r}")
    except smtplib.SMTPAuthenticationError:
        print("[notifier] ERROR: SMTP authentication failed. "
              "Check NOTIFY_GMAIL_APP_PASS — it must be a Gmail App Password, "
              "not your regular login password.")
    except Exception as e:
        print(f"[notifier] ERROR: Failed to send email — {e}")
