"""Automated documentation sync agent package."""

from .generator import DocumentationPatch, generate_documentation_update, render_pr_summary, run_sync_pipeline
from .notifier import Notification, redact_secrets, send_notification
from .parser import ChangeRecord, parse_git_diff, parse_name_status

__all__ = [
    "ChangeRecord",
    "DocumentationPatch",
    "Notification",
    "generate_documentation_update",
    "parse_git_diff",
    "parse_name_status",
    "redact_secrets",
    "render_pr_summary",
    "run_sync_pipeline",
    "send_notification",
]
