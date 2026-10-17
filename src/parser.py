"""Parsers for repository diff data and documentation-impact classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ChangeRecord:
    """Represents a single source change that may affect documentation."""

    path: str
    status: str
    change_type: str
    impact: str
    summary: str
    source_commit: str | None = None
    added_lines: int = 0
    deleted_lines: int = 0

    @property
    def normalized_path(self) -> str:
        return PurePosixPath(self.path).as_posix()


def _classify_change_type(path: str) -> str:
    normalized = path.lower()

    if any(keyword in normalized for keyword in ("openapi", "swagger", "api", "routes", "schema")):
        return "api"
    if any(keyword in normalized for keyword in ("config", "env", "yaml", "yml", "json", "helm", "docker")):
        return "configuration"
    if any(keyword in normalized for keyword in ("release", "changelog", "notes", "version")):
        return "release"
    if any(keyword in normalized for keyword in ("infra", "deploy", "k8s", "terraform")):
        return "deployment"
    return "general"


def _classify_impact(path: str) -> str:
    normalized = path.lower()
    if any(keyword in normalized for keyword in ("openapi", "swagger", "schema", "env", "config")):
        return "high"
    if any(keyword in normalized for keyword in ("release", "deploy", "helm", "docker")):
        return "medium"
    return "low"


def _build_summary(path: str, status: str, change_type: str) -> str:
    verb = {
        "A": "added",
        "M": "modified",
        "D": "removed",
        "R": "renamed",
        "C": "copied",
    }.get(status, "updated")
    return f"{verb} {change_type} definition at {path}"


def parse_name_status(raw_text: str, source_commit: str | None = None) -> list[ChangeRecord]:
    """Parse git diff --name-status output into structured change records."""

    results: list[ChangeRecord] = []
    for line in raw_text.splitlines():
        if not line.strip():
            continue

        match = re.match(r"^(A|M|D|R\d+|C\d+)\s+(.*)$", line)
        if not match:
            continue

        status_token = match.group(1)
        rest = match.group(2).strip()
        pieces = [part for part in re.split(r"\t+", rest) if part]

        if status_token.startswith("R") or status_token.startswith("C"):
            if len(pieces) < 2:
                continue
            source_path = pieces[0]
            target_path = pieces[-1]
            path = target_path
            status = status_token
        else:
            if not pieces:
                continue
            path = pieces[-1]
            status = status_token

        change_type = _classify_change_type(path)
        impact = _classify_impact(path)
        summary = _build_summary(path, status, change_type)
        results.append(
            ChangeRecord(
                path=path,
                status=status,
                change_type=change_type,
                impact=impact,
                summary=summary,
                source_commit=source_commit,
            )
        )

    return results


def parse_git_diff(diff_text: str, source_commit: str | None = None) -> list[ChangeRecord]:
    """Parse a git diff or name-status stream and normalize to ChangeRecord objects."""

    if not diff_text.strip():
        return []

    if re.search(r"^(A|M|D|R\d+|C\d+)\s+", diff_text, re.MULTILINE):
        return parse_name_status(diff_text, source_commit=source_commit)

    records: list[ChangeRecord] = []
    current_status: str | None = None
    current_path: str | None = None

    for line in diff_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("diff --git "):
            match = re.match(r"^diff --git a/(.+?) b/(.+)$", stripped)
            if match:
                current_path = match.group(2)
                current_status = "M"
            continue

        if stripped.startswith("new file mode"):
            current_status = "A"
            continue

        if stripped.startswith("deleted file mode"):
            current_status = "D"
            continue

        if stripped.startswith("rename from "):
            current_status = "R"
            current_path = stripped[len("rename from "):].strip()
            continue

        if stripped.startswith("rename to "):
            current_path = stripped[len("rename to "):].strip()
            continue

        if stripped.startswith("+++ ") and stripped != "+++ /dev/null":
            current_path = stripped[6:]
            if current_status is None:
                current_status = "M"
            continue

        if stripped == "--- /dev/null":
            current_status = "A"
            continue

        if stripped == "+++ /dev/null":
            current_status = "D"
            continue

        if stripped.startswith("@@") and current_path and current_status:
            records.append(
                ChangeRecord(
                    path=current_path,
                    status=current_status,
                    change_type=_classify_change_type(current_path),
                    impact=_classify_impact(current_path),
                    summary=_build_summary(current_path, current_status, _classify_change_type(current_path)),
                    source_commit=source_commit,
                )
            )
            current_status = None
            continue

    if current_path and current_status and not records:
        records.append(
            ChangeRecord(
                path=current_path,
                status=current_status,
                change_type=_classify_change_type(current_path),
                impact=_classify_impact(current_path),
                summary=_build_summary(current_path, current_status, _classify_change_type(current_path)),
                source_commit=source_commit,
            )
        )

    deduped: list[ChangeRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (record.path, record.status, record.summary)
        if key not in seen:
            deduped.append(record)
            seen.add(key)

    return deduped


def filter_relevant_changes(changes: Iterable[ChangeRecord]) -> list[ChangeRecord]:
    """Return only changes that are likely to require documentation updates."""

    relevant: list[ChangeRecord] = []
    for change in changes:
        normalized = change.path.lower()
        if any(keyword in normalized for keyword in ("docs", "api", "schema", "config", "release", "env", "helm", "docker", "yaml", "yml", "json")):
            relevant.append(change)
    return relevant


def summarize_change_set(changes: Sequence[ChangeRecord]) -> str:
    if not changes:
        return "No relevant source changes detected."

    return "\n".join(f"- {change.summary} [{change.impact}]" for change in changes)
