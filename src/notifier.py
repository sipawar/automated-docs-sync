"""Simple notification helpers for documentation sync review workflows."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request, error
import re


SECRET_PATTERNS = (
    r"(?i)(token|api[_-]?key|secret|password|passwd|auth)[=:\s]+[A-Za-z0-9_\-+/=]{3,}",
    r"(?i)(ghp_[A-Za-z0-9]{10,}|gho_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_\-]{20,})",
)


@dataclass(frozen=True)
class Notification:
    title: str
    body: str
    channel: str = "console"


def redact_secrets(value: str) -> str:
    """Mask common secret patterns before logging or sending notifications."""

    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = re.sub(pattern, lambda match: f"{match.group(1)}=[REDACTED]" if "=" in match.group(0) else "[REDACTED]", redacted)
    return redacted


def _write_github_summary(title: str, body: str) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    summary_file = Path(summary_path)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("a", encoding="utf-8") as handle:
        handle.write(f"## {title}\n\n{body}\n\n")


def send_notification(notification: Notification, webhook_url: str | None = None) -> bool:
    """Send a notification to a webhook or print the message locally."""

    safe_title = redact_secrets(notification.title)
    safe_body = redact_secrets(notification.body)
    payload = {
        "text": f"{safe_title}\n\n{safe_body}",
        "title": safe_title,
    }

    if notification.channel == "github-summary":
        _write_github_summary(safe_title, safe_body)
        return True

    if webhook_url:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:  # pragma: no cover
                return response.status in (200, 201, 202, 204)
        except error.URLError:
            # Fall back to local logging if the webhook cannot be reached.
            print(f"[{safe_title}] {safe_body}")
            return False

    print(f"[{safe_title}] {safe_body}")
    _write_github_summary(safe_title, safe_body)
    return True
