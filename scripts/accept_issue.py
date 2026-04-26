from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from issue_tools import (
    enrich_metadata,
    find_existing,
    infer_tags,
    is_safe_public_url,
    issue_from_event,
    issue_labels,
    load_event,
    make_paper_id,
    suggestion_from_issue,
    unique_paper_id,
)
from paperlib import DATA_DIR, ProjectError, is_http_url, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Accept a GitHub paper suggestion issue into data/papers.")
    parser.add_argument("--event", required=True, help="Path to the GitHub event JSON payload.")
    parser.add_argument("--accepted-at", help="ISO date or datetime. Defaults to the current UTC time.")
    parser.add_argument("--reviewer", help="Reviewer GitHub username. Defaults to the event sender.")
    parser.add_argument("--fetch-metadata", action="store_true", help="Best-effort metadata lookup via public APIs.")
    parser.add_argument("--force", action="store_true", help="Create or update even if the issue has no accepted label.")
    args = parser.parse_args()

    try:
        result = accept_issue(
            Path(args.event),
            accepted_at=args.accepted_at,
            reviewer=args.reviewer,
            fetch_metadata=args.fetch_metadata,
            force=args.force,
        )
    except (ProjectError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


def accept_issue(
    event_path: Path,
    accepted_at: str | None = None,
    reviewer: str | None = None,
    fetch_metadata: bool = False,
    force: bool = False,
) -> str:
    event = load_event(event_path)
    issue = issue_from_event(event)
    labels = {label.lower() for label in issue_labels(issue)}
    featured = "featured" in labels
    accepted = "accepted" in labels
    reviewer = reviewer or ((event.get("sender") or {}).get("login")) or "maintainer"

    suggestion = suggestion_from_issue(issue)
    existing = find_existing({"issue": suggestion.get("issue")})
    if existing:
        update_existing(existing.path, existing.data, featured=featured, reviewer=reviewer)
        return f"Updated existing accepted paper: {existing.path}"

    if not accepted and not force:
        return "Issue is not labeled accepted; no paper record created."

    url = suggestion.get("url", "")
    if not is_http_url(url):
        raise ProjectError("accepted issue must include an absolute http(s) paper URL")
    if not is_safe_public_url(url):
        raise ProjectError("accepted issue must include a public paper URL; local or private network URLs are not allowed")

    metadata = enrich_metadata(url, title_hint=str(suggestion.get("title") or ""), fetch=fetch_metadata)
    metadata["code"] = metadata.get("code") or code_link_from_suggestion(str(suggestion.get("code") or ""))
    metadata["project"] = metadata.get("project") or project_link_from_suggestion(str(suggestion.get("code") or ""))
    title = str(metadata.get("title") or suggestion.get("title") or f"Paper suggestion #{suggestion.get('issue')}").strip()
    accepted_at = accepted_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    publication_date = publication_date_from_metadata(metadata, accepted_at)
    year = int(metadata.get("year") or publication_date[:4])
    base_id = make_paper_id({**metadata, "title": title}, suggestion.get("issue"), year)
    paper_id = unique_paper_id(base_id, suggestion.get("issue"))
    tags = infer_tags(
        "\n".join(str(value or "") for value in (title, suggestion.get("note"), metadata.get("source", ""), metadata.get("abstract", ""))),
        explicit_tags=str(suggestion.get("suggested_tags") or ""),
    )
    note = str(suggestion.get("note") or "").strip()

    paper: dict[str, Any] = {
        "id": paper_id,
        "title": title,
        "authors": metadata.get("authors") or ["Unknown"],
        "year": year,
        "date": publication_date,
        "accepted_at": accepted_at,
        "source": metadata.get("source") or "unknown",
        "doi": metadata.get("doi", ""),
        "url": metadata.get("url") or url,
        "pdf": metadata.get("pdf", ""),
        "code": metadata.get("code", ""),
        "project": metadata.get("project", ""),
        "preprint_url": metadata.get("preprint_url", ""),
        "published_url": metadata.get("published_url", ""),
        "topics": tags["topics"],
        "methods": tags["methods"],
        "evidence": tags["evidence"],
        "applications": tags["applications"],
        "one_liner": first_sentence(note) or "No curator summary supplied.",
        "why_it_matters": note or "No curator note supplied.",
        "curator": reviewer,
        "featured": featured,
        "issue": suggestion.get("issue"),
        "submitted_by": suggestion.get("submitted_by", ""),
        "reviewed_by": reviewer,
        "notes": f"Accepted from GitHub issue #{suggestion.get('issue')}.",
        "curation": {
            "status": "accepted",
            "issue": suggestion.get("issue"),
            "submitted_by": suggestion.get("submitted_by", ""),
            "reviewed_by": reviewer,
            "featured": featured,
        },
    }

    duplicate = find_existing(paper)
    if duplicate:
        update_existing(duplicate.path, duplicate.data, featured=featured, reviewer=reviewer)
        return f"Existing duplicate accepted paper updated: {duplicate.path}"

    out_path = DATA_DIR / "papers" / str(year) / f"{paper_id}.yml"
    write_text(out_path, yaml.safe_dump(paper, sort_keys=False, allow_unicode=False))
    return f"Created accepted paper: {out_path}"


def update_existing(path: Path, data: dict[str, Any], featured: bool, reviewer: str) -> None:
    data = dict(data)
    data["featured"] = bool(data.get("featured") or featured)
    data["reviewed_by"] = data.get("reviewed_by") or reviewer
    curation = data.get("curation")
    if not isinstance(curation, dict):
        curation = {}
    curation["status"] = curation.get("status") or "accepted"
    curation["reviewed_by"] = curation.get("reviewed_by") or reviewer
    curation["featured"] = bool(curation.get("featured") or featured)
    data["curation"] = curation
    write_text(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=False))


def publication_date_from_metadata(metadata: dict[str, Any], accepted_at: str) -> str:
    value = str(metadata.get("date") or "")
    if len(value) == 10:
        return value
    return accepted_at[:10]


def code_link_from_suggestion(value: str) -> str:
    return value if "github.com" in value.lower() else ""


def project_link_from_suggestion(value: str) -> str:
    return value if value and "github.com" not in value.lower() else ""


def first_sentence(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        return ""
    match = next((index for index in (cleaned.find("."), cleaned.find("!"), cleaned.find("?")) if index > 0), -1)
    if match > 0:
        return cleaned[: match + 1]
    return cleaned[:220]


if __name__ == "__main__":
    sys.exit(main())
