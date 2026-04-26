from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

from issue_tools import normalize_url
from paperlib import (
    DATA_DIR,
    TAG_GROUPS,
    WEEKLY_DIR,
    PaperRecord,
    ProjectError,
    load_papers,
    load_yaml,
    normalize_key,
    write_text,
)


TEXT_FIELDS = (
    "title",
    "date",
    "source",
    "doi",
    "url",
    "pdf",
    "code",
    "project",
    "preprint_url",
    "published_url",
    "one_liner",
    "why_it_matters",
    "notes",
)
CLEARABLE_FIELDS = (
    "doi",
    "pdf",
    "code",
    "project",
    "preprint_url",
    "published_url",
    "notes",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Owner-only paper metadata update/delete helper.")
    parser.add_argument("--selector", required=True, help="Paper id, DOI, or URL.")
    parser.add_argument("--delete", action="store_true", help="Delete the selected paper record.")
    parser.add_argument("--reviewer", default="owner", help="Reviewer username.")
    parser.add_argument("--featured", choices=("keep", "true", "false"), default="keep")
    parser.add_argument("--clear", help="Comma-separated optional URL/text fields to clear.")
    parser.add_argument("--authors", help="Comma-separated author list.")
    parser.add_argument("--year", type=int, help="Publication year.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would change without writing files.")

    for field in TEXT_FIELDS:
        parser.add_argument(f"--{field.replace('_', '-')}", dest=field)
    for group in TAG_GROUPS:
        parser.add_argument(f"--{group}", help=f"Comma-separated canonical {group} tag ids.")

    args = parser.parse_args()

    try:
        result = manage_paper(
            selector=args.selector,
            delete=args.delete,
            reviewer=args.reviewer,
            featured=args.featured,
            clear=args.clear or "",
            authors=args.authors,
            year=args.year,
            text_updates={field: getattr(args, field) for field in TEXT_FIELDS},
            tag_updates={group: getattr(args, group) for group in TAG_GROUPS},
            dry_run=args.dry_run,
        )
    except (ProjectError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(result)
    return 0


def manage_paper(
    selector: str,
    delete: bool = False,
    reviewer: str = "owner",
    featured: str = "keep",
    clear: str = "",
    authors: str | None = None,
    year: int | None = None,
    text_updates: dict[str, str | None] | None = None,
    tag_updates: dict[str, str | None] | None = None,
    dry_run: bool = False,
) -> str:
    record = find_paper(selector)
    reviewer = reviewer.strip() or "owner"

    if delete:
        if dry_run:
            return f"Would delete paper: {record.paper_id} ({record.path})"
        record.path.unlink()
        pruned = prune_weekly_overrides(record.paper_id)
        suffix = f" Pruned weekly overrides: {', '.join(str(path) for path in pruned)}." if pruned else ""
        return f"Deleted paper: {record.path}.{suffix}"

    data = dict(record.data)
    changed: list[str] = []
    clear_fields = {field.strip() for field in clear.split(",") if field.strip()}
    invalid_clear_fields = clear_fields - set(CLEARABLE_FIELDS)
    if invalid_clear_fields:
        raise ProjectError(f"unknown clear fields: {', '.join(sorted(invalid_clear_fields))}")

    for field in clear_fields:
        if data.get(field) != "":
            data[field] = ""
            changed.append(field)

    for field, value in (text_updates or {}).items():
        if value is None or value == "":
            continue
        if data.get(field) != value:
            data[field] = value
            changed.append(field)
            if field == "date" and year is None and len(value) >= 4 and value[:4].isdigit():
                year = int(value[:4])

    if authors is not None and authors != "":
        parsed_authors = parse_list(authors)
        if not parsed_authors:
            raise ProjectError("authors update cannot be empty")
        if data.get("authors") != parsed_authors:
            data["authors"] = parsed_authors
            changed.append("authors")

    if year is not None:
        if year < 1900 or year > 2100:
            raise ProjectError("year must be between 1900 and 2100")
        if data.get("year") != year:
            data["year"] = year
            changed.append("year")

    for group, value in (tag_updates or {}).items():
        if value is None or value == "":
            continue
        parsed = parse_list(value)
        if not parsed:
            raise ProjectError(f"{group} update cannot be empty")
        if data.get(group) != parsed:
            data[group] = parsed
            changed.append(group)

    if featured != "keep":
        featured_value = featured == "true"
        if bool(data.get("featured")) != featured_value:
            data["featured"] = featured_value
            changed.append("featured")
        curation = data.get("curation")
        if not isinstance(curation, dict):
            curation = {}
        if bool(curation.get("featured")) != featured_value:
            curation["featured"] = featured_value
            data["curation"] = curation
            if "featured" not in changed:
                changed.append("featured")

    data["reviewed_by"] = reviewer
    curation = data.get("curation")
    if not isinstance(curation, dict):
        curation = {}
    curation["reviewed_by"] = reviewer
    data["curation"] = curation

    if dry_run:
        if not changed:
            return f"No metadata changes for {record.paper_id}."
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=False).rstrip()

    if not changed:
        return f"No metadata changes for {record.path}."

    write_text(record.path, yaml.safe_dump(data, sort_keys=False, allow_unicode=False))
    return f"Updated paper: {record.path}. Fields: {', '.join(changed)}"


def find_paper(selector: str) -> PaperRecord:
    value = selector.strip()
    if not value:
        raise ProjectError("selector cannot be empty")
    normalized = normalize_key(value)
    normalized_url = normalize_url(value)
    matches: list[PaperRecord] = []
    for record in load_papers():
        data = record.data
        if record.paper_id == value:
            matches.append(record)
            continue
        if normalized and normalize_key(data.get("doi", "")) == normalized:
            matches.append(record)
            continue
        if normalized_url and normalize_url(str(data.get("url", ""))) == normalized_url:
            matches.append(record)
            continue
        for field in ("pdf", "preprint_url", "published_url"):
            if normalized_url and normalize_url(str(data.get(field, ""))) == normalized_url:
                matches.append(record)
                break

    unique_matches = {record.path: record for record in matches}
    if not unique_matches:
        raise ProjectError(f"no paper matched selector: {selector}")
    if len(unique_matches) > 1:
        options = ", ".join(record.paper_id for record in unique_matches.values())
        raise ProjectError(f"selector matched multiple papers: {options}")
    return next(iter(unique_matches.values()))


def parse_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def prune_weekly_overrides(paper_id: str) -> list[Path]:
    changed: list[Path] = []
    for path in sorted(WEEKLY_DIR.glob("*.yml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            continue
        touched = False
        sections = data.get("sections")
        if isinstance(sections, dict):
            for section_id in list(sections.keys()):
                section = sections.get(section_id)
                if not isinstance(section, dict):
                    continue
                papers = section.get("papers")
                if not isinstance(papers, list):
                    continue
                filtered = [value for value in papers if value != paper_id]
                if filtered != papers:
                    touched = True
                    section["papers"] = filtered
                if not filtered:
                    touched = True
                    sections.pop(section_id)
        commentary = data.get("commentary")
        if isinstance(commentary, dict) and paper_id in commentary:
            touched = True
            commentary.pop(paper_id)
        if data.get("pick_of_the_week") == paper_id:
            touched = True
            data["pick_of_the_week"] = first_section_paper(data)
        if not touched:
            continue
        if not data.get("sections") or not first_section_paper(data):
            path.unlink()
        else:
            write_text(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=False))
        changed.append(path)
    return changed


def first_section_paper(data: dict[str, Any]) -> str:
    sections = data.get("sections")
    if not isinstance(sections, dict):
        return ""
    for section in sections.values():
        if isinstance(section, dict):
            papers = section.get("papers")
            if isinstance(papers, list) and papers:
                return str(papers[0])
    return ""


if __name__ == "__main__":
    sys.exit(main())
