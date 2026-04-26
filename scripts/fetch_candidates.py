from __future__ import annotations

from typing import Any


class FetcherNotImplementedError(NotImplementedError):
    """Raised when a future automatic candidate fetcher is called."""


def fetch_arxiv_candidates() -> list[dict[str, Any]]:
    raise FetcherNotImplementedError("arXiv candidate fetching is not implemented yet.")


def fetch_biorxiv_candidates() -> list[dict[str, Any]]:
    raise FetcherNotImplementedError("bioRxiv candidate fetching is not implemented yet.")


def fetch_pubmed_candidates() -> list[dict[str, Any]]:
    raise FetcherNotImplementedError("PubMed candidate fetching is not implemented yet.")


def normalize_candidate(raw: dict[str, Any], source: str) -> dict[str, Any]:
    """Normalize a future fetched record into the candidate YAML shape.

    This function defines the stable interface for future automation. It does
    not accept candidates into `data/papers/`; it only prepares reviewable
    candidate metadata.
    """

    return {
        "title": str(raw.get("title", "")).strip(),
        "authors": raw.get("authors", []),
        "source": source,
        "url": str(raw.get("url", "")).strip(),
        "doi": str(raw.get("doi", "")).strip(),
        "suggested_topics": [],
        "suggested_methods": [],
        "suggested_evidence": [],
        "suggested_applications": [],
        "why_relevant": "",
        "status": "pending-review",
    }


def main() -> int:
    print("Automatic candidate fetching is intentionally disabled in this MVP.")
    print("Use GitHub issues or candidates/manual/ for paper recommendations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
