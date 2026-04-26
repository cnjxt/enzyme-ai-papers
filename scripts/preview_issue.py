from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from issue_tools import (
    enrich_metadata,
    find_existing,
    infer_tags,
    is_safe_public_url,
    issue_from_event,
    load_event,
    suggestion_from_issue,
)
from paperlib import ProjectError, is_http_url, write_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a review preview for a paper suggestion issue.")
    parser.add_argument("--event", required=True, help="Path to the GitHub event JSON payload.")
    parser.add_argument("--output", help="Optional markdown file to write.")
    parser.add_argument("--fetch-metadata", action="store_true", help="Best-effort metadata lookup via public APIs.")
    args = parser.parse_args()

    try:
        preview = build_preview(Path(args.event), fetch_metadata=args.fetch_metadata)
    except (ProjectError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        write_text(Path(args.output), preview)
    else:
        print(preview)
    return 0


def build_preview(event_path: Path, fetch_metadata: bool = False) -> str:
    issue = issue_from_event(load_event(event_path))
    suggestion = suggestion_from_issue(issue)
    url = suggestion.get("url", "")
    if not is_http_url(url):
        return """### Paper suggestion preview

No paper URL was found. Please add a DOI, arXiv, bioRxiv, PubMed, journal, or project URL so maintainers can review the suggestion.
"""
    if not is_safe_public_url(url):
        return """### Paper suggestion preview

The submitted URL is not a public web URL that the automation can review. Please use a DOI, arXiv, bioRxiv, PubMed, journal, or public project URL.
"""

    metadata = enrich_metadata(url, title_hint=str(suggestion.get("title") or ""), fetch=fetch_metadata)
    title = metadata.get("title") or suggestion.get("title") or "(metadata not resolved yet)"
    note = str(suggestion.get("note") or "").strip()
    tag_suggestions = infer_tags(
        "\n".join(str(value or "") for value in (title, note, metadata.get("source", ""), metadata.get("abstract", ""))),
        explicit_tags=str(suggestion.get("suggested_tags") or ""),
    )
    candidate = {
        "issue": suggestion.get("issue"),
        "title": title,
        "url": url,
        "doi": metadata.get("doi", ""),
    }
    existing = find_existing(candidate)
    duplicate_note = f"\n\nExisting accepted record: `{existing.path}`" if existing else ""
    tags = " ".join(f"`{tag}`" for values in tag_suggestions.values() for tag in values)
    authors = metadata.get("authors") or ["Unknown"]

    return f"""### Paper suggestion preview

This issue can be accepted by adding the `accepted` label.

- **Title:** {title}
- **URL:** {url}
- **Source:** {metadata.get("source") or "unknown"}
- **DOI:** {metadata.get("doi") or "not detected"}
- **Authors:** {", ".join(authors)}
- **Suggested tags:** {tags}

**Submitter note**

{note or "_No note provided._"}{duplicate_note}
"""


if __name__ == "__main__":
    raise SystemExit(main())
