from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from issue_tools import infer_tags, make_paper_id, unique_paper_id
from paperlib import DATA_DIR, ProjectError, is_http_url, load_yaml, write_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create an accepted paper YAML draft from a manual candidate."
    )
    parser.add_argument("candidate", help="Path to a candidate YAML file.")
    parser.add_argument("--id", help="Accepted paper ID. Defaults to a generated slug.")
    parser.add_argument("--year", type=int, help="Publication or preprint year. Defaults to candidate year or today.")
    parser.add_argument("--date", help="Publication or curation date in YYYY-MM-DD. Defaults to candidate date or today.")
    parser.add_argument("--accepted-at", help="Accepted date or datetime. Defaults to the current UTC time.")
    args = parser.parse_args()

    try:
        output = promote_candidate(Path(args.candidate), args.id, args.year, args.date, args.accepted_at)
    except ProjectError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Created draft: {output}")
    return 0


def promote_candidate(
    candidate_path: Path,
    paper_id: str | None = None,
    year: int | None = None,
    date: str | None = None,
    accepted_at: str | None = None,
) -> Path:
    if not candidate_path.exists():
        raise ProjectError(f"candidate file does not exist: {candidate_path}")

    candidate = load_yaml(candidate_path)
    if not isinstance(candidate, dict):
        raise ProjectError("candidate file must contain a mapping")

    title = str(candidate.get("title", "")).strip()
    url = str(candidate.get("url", "")).strip()
    if not title:
        raise ProjectError("candidate title is required")
    if not is_http_url(url):
        raise ProjectError("candidate url must be an absolute http(s) URL")

    accepted_at = accepted_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    date = date or str(candidate.get("date") or accepted_at[:10])
    year = year or int(candidate.get("year") or date[:4])
    metadata = {
        "identifier": candidate.get("identifier", ""),
        "doi": candidate.get("doi", ""),
        "title": title,
    }
    paper_id = paper_id or unique_paper_id(make_paper_id(metadata, candidate.get("issue", "manual"), year), candidate.get("issue", "manual"))
    tags = infer_tags(
        "\n".join(
            str(value or "")
            for value in (
                title,
                candidate.get("why_relevant"),
                candidate.get("one_liner"),
                candidate.get("source"),
            )
        )
    )

    accepted: dict[str, Any] = {
        "id": paper_id,
        "title": title,
        "authors": candidate.get("authors") or ["Unknown"],
        "year": year,
        "date": date,
        "accepted_at": accepted_at,
        "source": candidate.get("source", "unknown"),
        "doi": candidate.get("doi", ""),
        "url": url,
        "pdf": candidate.get("pdf", ""),
        "code": candidate.get("code", ""),
        "project": candidate.get("project", ""),
        "preprint_url": candidate.get("preprint_url", ""),
        "published_url": candidate.get("published_url", ""),
        "topics": candidate.get("suggested_topics") or tags["topics"],
        "methods": candidate.get("suggested_methods") or tags["methods"],
        "evidence": candidate.get("suggested_evidence") or tags["evidence"],
        "applications": candidate.get("suggested_applications") or tags["applications"],
        "one_liner": candidate.get("one_liner", "TODO: Add a concise contribution summary."),
        "why_it_matters": candidate.get(
            "why_relevant",
            "TODO: Add an original curator note explaining why this paper matters.",
        ),
        "curator": candidate.get("curator", "maintainer"),
        "featured": bool(candidate.get("featured", False)),
        "issue": candidate.get("issue", ""),
        "submitted_by": candidate.get("submitted_by", ""),
        "reviewed_by": candidate.get("curator", "maintainer"),
        "notes": "Promoted from candidate. Review all fields before merging.",
        "curation": {
            "status": "accepted",
            "issue": candidate.get("issue", ""),
            "submitted_by": candidate.get("submitted_by", ""),
            "reviewed_by": candidate.get("curator", "maintainer"),
            "featured": bool(candidate.get("featured", False)),
        },
    }

    out_dir = DATA_DIR / "papers" / str(year)
    out_path = out_dir / f"{paper_id}.yml"
    if out_path.exists():
        raise ProjectError(f"output file already exists: {out_path}")

    content = yaml.safe_dump(accepted, sort_keys=False, allow_unicode=False)
    write_text(out_path, content)
    return out_path


if __name__ == "__main__":
    sys.exit(main())
