from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

import yaml

from accept_issue import (
    code_link_from_suggestion,
    first_sentence,
    project_link_from_suggestion,
    publication_date_from_metadata,
    update_existing,
)
from issue_tools import (
    enrich_metadata,
    find_existing,
    infer_tags,
    is_safe_public_url,
    make_paper_id,
)
from paperlib import DATA_DIR, ProjectError, is_http_url, load_papers, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a paper directly from a URL.")
    parser.add_argument("--url", required=True, help="Paper, DOI, preprint, PubMed, or project URL.")
    parser.add_argument("--title", help="Optional title override.")
    parser.add_argument("--note", help="Optional curator note used for one_liner and why_it_matters.")
    parser.add_argument("--tags", help="Optional free-text tag hints.")
    parser.add_argument("--code", help="Optional code, project, dataset, or benchmark URL.")
    parser.add_argument("--accepted-at", help="ISO date or datetime. Defaults to the current UTC time.")
    parser.add_argument("--reviewer", default="owner", help="Curator username. Defaults to owner.")
    parser.add_argument("--featured", action="store_true", help="Set the reserved featured flag.")
    parser.add_argument("--fetch-metadata", action="store_true", help="Best-effort metadata lookup via public APIs.")
    parser.add_argument("--dry-run", action="store_true", help="Print the generated YAML without writing files.")
    args = parser.parse_args()

    try:
        result = publish_url(
            url=args.url,
            title=args.title or "",
            note=args.note or "",
            tags=args.tags or "",
            code=args.code or "",
            accepted_at=args.accepted_at,
            reviewer=args.reviewer,
            featured=args.featured,
            fetch_metadata=args.fetch_metadata,
            dry_run=args.dry_run,
        )
    except (ProjectError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


def publish_url(
    url: str,
    title: str = "",
    note: str = "",
    tags: str = "",
    code: str = "",
    accepted_at: str | None = None,
    reviewer: str = "owner",
    featured: bool = False,
    fetch_metadata: bool = False,
    dry_run: bool = False,
) -> str:
    url = url.strip()
    if not is_http_url(url):
        raise ProjectError("paper URL must be an absolute http(s) URL")
    if not is_safe_public_url(url):
        raise ProjectError("paper URL must be public; local or private network URLs are not allowed")

    metadata = enrich_metadata(url, title_hint=title.strip(), fetch=fetch_metadata)
    metadata["code"] = metadata.get("code") or code_link_from_suggestion(code)
    metadata["project"] = metadata.get("project") or project_link_from_suggestion(code)
    resolved_title = str(metadata.get("title") or title or "").strip()
    if not resolved_title:
        raise ProjectError("title could not be resolved; pass --title or enable metadata fetch for a supported URL")

    accepted_at = accepted_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    publication_date = publication_date_from_metadata(metadata, accepted_at)
    year = int(metadata.get("year") or publication_date[:4])
    tag_groups = infer_tags(
        "\n".join(str(value or "") for value in (resolved_title, note, metadata.get("source", ""), metadata.get("abstract", ""))),
        explicit_tags=tags,
    )
    paper = build_paper_record(
        metadata=metadata,
        url=url,
        title=resolved_title,
        note=note.strip(),
        accepted_at=accepted_at,
        publication_date=publication_date,
        year=year,
        tags=tag_groups,
        reviewer=reviewer.strip() or "owner",
        featured=featured,
    )

    duplicate = find_existing(paper)
    if duplicate:
        if dry_run:
            return f"Existing duplicate would be updated: {duplicate.path}"
        update_existing(duplicate.path, duplicate.data, featured=featured, reviewer=paper["reviewed_by"])
        return f"Existing duplicate accepted paper updated: {duplicate.path}"

    if dry_run:
        return yaml.safe_dump(paper, sort_keys=False, allow_unicode=False).rstrip()

    out_path = DATA_DIR / "papers" / str(year) / f"{paper['id']}.yml"
    write_text(out_path, yaml.safe_dump(paper, sort_keys=False, allow_unicode=False))
    return f"Created accepted paper: {out_path}"


def build_paper_record(
    metadata: dict[str, Any],
    url: str,
    title: str,
    note: str,
    accepted_at: str,
    publication_date: str,
    year: int,
    tags: dict[str, list[str]],
    reviewer: str,
    featured: bool,
) -> dict[str, Any]:
    base_id = make_paper_id({**metadata, "title": title}, "", year)
    paper_id = unique_direct_paper_id(base_id)
    one_liner = first_sentence(note) or f"Directly published paper for enzyme AI curation: {title}."
    why_it_matters = note or f"Directly published by {reviewer} from the project owner URL workflow."

    return {
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
        "one_liner": one_liner,
        "why_it_matters": why_it_matters,
        "curator": reviewer,
        "featured": featured,
        "issue": "",
        "submitted_by": reviewer,
        "reviewed_by": reviewer,
        "notes": f"Published directly from URL by {reviewer}.",
        "curation": {
            "status": "accepted",
            "issue": "",
            "submitted_by": reviewer,
            "reviewed_by": reviewer,
            "featured": featured,
        },
    }


def unique_direct_paper_id(base_id: str) -> str:
    existing = {record.paper_id for record in load_papers()}
    if base_id not in existing:
        return base_id
    candidate = f"{base_id}-direct"
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}-{index}" in existing:
        index += 1
    return f"{candidate}-{index}"


if __name__ == "__main__":
    sys.exit(main())
