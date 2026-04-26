from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PAPERS_DIR = DATA_DIR / "papers"
WEEKLY_DIR = DATA_DIR / "weekly"
TAXONOMY_PATH = DATA_DIR / "taxonomy.yml"
DOCS_DIR = ROOT / "docs"

REQUIRED_PAPER_FIELDS = {
    "id",
    "title",
    "authors",
    "year",
    "date",
    "source",
    "url",
    "topics",
    "methods",
    "evidence",
    "applications",
    "one_liner",
    "why_it_matters",
}

REQUIRED_WEEKLY_FIELDS = {
    "week",
    "title",
    "date",
    "summary",
}

TAG_GROUPS = ("topics", "methods", "evidence", "applications")
ID_RE = re.compile(r"^\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
FLEXIBLE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?$")


class ProjectError(Exception):
    """Raised for validation and project data errors."""


@dataclass(frozen=True)
class PaperRecord:
    path: Path
    data: dict[str, Any]

    @property
    def paper_id(self) -> str:
        return str(self.data["id"])

    @property
    def title(self) -> str:
        return str(self.data["title"])

    @property
    def year(self) -> int:
        return int(self.data["year"])

    @property
    def date(self) -> str:
        return str(self.data["date"])

    @property
    def accepted_at(self) -> str:
        return str(self.data.get("accepted_at") or self.data["date"])

    @property
    def week(self) -> str:
        return iso_week(self.accepted_at)

    @property
    def featured(self) -> bool:
        curation = self.data.get("curation", {})
        return bool(self.data.get("featured") or (isinstance(curation, dict) and curation.get("featured")))


@dataclass(frozen=True)
class WeeklyRecord:
    path: Path
    data: dict[str, Any]

    @property
    def week(self) -> str:
        return str(self.data["week"])


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_taxonomy() -> dict[str, Any]:
    taxonomy = load_yaml(TAXONOMY_PATH)
    if not isinstance(taxonomy, dict):
        raise ProjectError(f"{TAXONOMY_PATH} must contain a mapping")
    for group in TAG_GROUPS:
        if group not in taxonomy or not isinstance(taxonomy[group], dict):
            raise ProjectError(f"taxonomy is missing group: {group}")
    return taxonomy


def taxonomy_labels(taxonomy: dict[str, Any], group: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for tag, meta in taxonomy[group].items():
        if isinstance(meta, dict):
            labels[tag] = str(meta.get("label", tag))
        else:
            labels[tag] = tag
    return labels


def load_papers() -> list[PaperRecord]:
    records: list[PaperRecord] = []
    for path in sorted(PAPERS_DIR.glob("*/*.yml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise ProjectError(f"{path} must contain a mapping")
        records.append(PaperRecord(path=path, data=data))
    return records


def load_weeklies() -> list[WeeklyRecord]:
    records: list[WeeklyRecord] = []
    for path in sorted(WEEKLY_DIR.glob("*.yml")):
        data = load_yaml(path)
        if not isinstance(data, dict):
            raise ProjectError(f"{path} must contain a mapping")
        records.append(WeeklyRecord(path=path, data=data))
    return records


def index_papers(records: list[PaperRecord]) -> dict[str, PaperRecord]:
    by_id: dict[str, PaperRecord] = {}
    for record in records:
        paper_id = record.paper_id
        if paper_id in by_id:
            other = by_id[paper_id].path
            raise ProjectError(f"duplicate paper id {paper_id}: {other} and {record.path}")
        by_id[paper_id] = record
    return by_id


def validate_all() -> list[str]:
    taxonomy = load_taxonomy()
    papers = load_papers()
    paper_index = index_papers(papers)
    weeklies = load_weeklies()

    errors: list[str] = []
    for record in papers:
        errors.extend(validate_paper(record, taxonomy))
    errors.extend(validate_duplicates(papers))
    for record in weeklies:
        errors.extend(validate_weekly(record, paper_index))
    return errors


def validate_paper(record: PaperRecord, taxonomy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = record.data
    path = record.path

    missing = sorted(REQUIRED_PAPER_FIELDS - data.keys())
    if missing:
        errors.append(f"{path}: missing required fields: {', '.join(missing)}")

    paper_id = data.get("id")
    if not isinstance(paper_id, str) or not FLEXIBLE_ID_RE.match(paper_id):
        errors.append(f"{path}: id must match {FLEXIBLE_ID_RE.pattern}")

    if isinstance(paper_id, str) and path.stem != paper_id:
        errors.append(f"{path}: filename must match id")

    year = data.get("year")
    if not isinstance(year, int) or year < 1900 or year > 2100:
        errors.append(f"{path}: year must be an integer between 1900 and 2100")

    date = data.get("date")
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append(f"{path}: date must use YYYY-MM-DD")

    accepted_at = data.get("accepted_at")
    if accepted_at not in (None, ""):
        if not isinstance(accepted_at, str) or not DATETIME_RE.match(accepted_at):
            errors.append(f"{path}: accepted_at must use YYYY-MM-DD or an ISO datetime")
        else:
            try:
                parse_record_date(accepted_at)
            except ValueError:
                errors.append(f"{path}: accepted_at is not a valid date or datetime")

    authors = data.get("authors")
    if not isinstance(authors, list) or not authors or not all(is_nonempty_string(x) for x in authors):
        errors.append(f"{path}: authors must be a non-empty list of strings")

    for field in ("title", "source", "one_liner", "why_it_matters"):
        if not is_nonempty_string(data.get(field)):
            errors.append(f"{path}: {field} must be a non-empty string")

    url = data.get("url")
    if not is_http_url(url):
        errors.append(f"{path}: url must be an absolute http(s) URL")

    for optional_url in ("pdf", "code", "project", "preprint_url", "published_url"):
        value = data.get(optional_url)
        if value not in (None, "") and not is_http_url(value):
            errors.append(f"{path}: {optional_url} must be empty or an absolute http(s) URL")

    for group in TAG_GROUPS:
        values = data.get(group)
        if not isinstance(values, list) or not values:
            errors.append(f"{path}: {group} must be a non-empty list")
            continue
        allowed = set(taxonomy[group].keys())
        for value in values:
            if value not in allowed:
                errors.append(f"{path}: unknown {group} tag: {value}")

    return errors


def validate_duplicates(records: list[PaperRecord]) -> list[str]:
    errors: list[str] = []
    seen_title: dict[str, Path] = {}
    seen_doi: dict[str, Path] = {}

    for record in records:
        title = normalize_key(record.data.get("title", ""))
        if title:
            if title in seen_title:
                errors.append(f"{record.path}: duplicate title with {seen_title[title]}")
            else:
                seen_title[title] = record.path

        doi = normalize_key(record.data.get("doi", ""))
        if doi:
            if doi in seen_doi:
                errors.append(f"{record.path}: duplicate doi with {seen_doi[doi]}")
            else:
                seen_doi[doi] = record.path

    return errors


def validate_weekly(record: WeeklyRecord, paper_index: dict[str, PaperRecord]) -> list[str]:
    errors: list[str] = []
    data = record.data
    path = record.path

    missing = sorted(REQUIRED_WEEKLY_FIELDS - data.keys())
    if missing:
        errors.append(f"{path}: missing required fields: {', '.join(missing)}")

    week = data.get("week")
    if not isinstance(week, str) or not WEEK_RE.match(week):
        errors.append(f"{path}: week must match {WEEK_RE.pattern}")
    elif path.stem != week:
        errors.append(f"{path}: filename must match week")

    date = data.get("date")
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append(f"{path}: date must use YYYY-MM-DD")

    for field in ("title", "summary"):
        if not is_nonempty_string(data.get(field)):
            errors.append(f"{path}: {field} must be a non-empty string")

    pick = data.get("pick_of_the_week")
    if pick is not None and (not isinstance(pick, str) or pick not in paper_index):
        errors.append(f"{path}: pick_of_the_week must reference an accepted paper id")

    sections = data.get("sections")
    if sections is not None:
        if not isinstance(sections, dict):
            errors.append(f"{path}: sections must be a mapping")
            sections = {}
        for section_id, section in sections.items():
            if not isinstance(section, dict):
                errors.append(f"{path}: section {section_id} must be a mapping")
                continue
            if not is_nonempty_string(section.get("title")):
                errors.append(f"{path}: section {section_id} needs a title")
            paper_ids = section.get("papers")
            if not isinstance(paper_ids, list) or not paper_ids:
                errors.append(f"{path}: section {section_id} needs a non-empty paper list")
                continue
            for paper_id in paper_ids:
                if paper_id not in paper_index:
                    errors.append(f"{path}: section {section_id} references unknown paper id {paper_id}")

    commentary = data.get("commentary", {})
    if commentary is not None and not isinstance(commentary, dict):
        errors.append(f"{path}: commentary must be a mapping")
    elif isinstance(commentary, dict):
        for paper_id in commentary:
            if paper_id not in paper_index:
                errors.append(f"{path}: commentary references unknown paper id {paper_id}")

    return errors


def sorted_papers(records: list[PaperRecord]) -> list[PaperRecord]:
    return sorted(records, key=lambda record: (parse_record_date(record.accepted_at), record.paper_id), reverse=True)


def parse_record_date(value: str) -> date:
    raw = str(value).strip()
    if not raw:
        raise ValueError("empty date")
    if len(raw) == 10:
        return date.fromisoformat(raw)
    normalized = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).date()


def iso_week(value: str) -> str:
    parsed = parse_record_date(value)
    year, week, _weekday = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def markdown_escape(text: Any) -> str:
    value = str(text)
    return value.replace("|", "\\|")


def format_links(paper: dict[str, Any]) -> str:
    links: list[str] = []
    for field, label in (
        ("url", "paper"),
        ("pdf", "pdf"),
        ("code", "code"),
        ("project", "project"),
    ):
        value = paper.get(field)
        if value:
            links.append(f"[{label}]({value})")
    return " · ".join(links)


def format_tags(paper: dict[str, Any]) -> str:
    tags: list[str] = []
    for group in TAG_GROUPS:
        tags.extend(str(tag) for tag in paper.get(group, []))
    return " ".join(f"`{tag}`" for tag in tags)


def paper_card(record: PaperRecord, commentary: str | None = None) -> str:
    paper = record.data
    authors = ", ".join(paper.get("authors", []))
    links = format_links(paper)
    tags = format_tags(paper)
    note = commentary or str(paper.get("why_it_matters", ""))
    lines = [
        f"### {paper['title']}",
        "",
        f"**Authors:** {authors}",
        f"**Source / Year:** {paper['source']}, {paper['year']}",
        f"**Links:** {links}",
        f"**Tags:** {tags}",
        "",
        f"**Why it matters:** {note}",
        "",
    ]
    return "\n".join(lines)


def compact_paper_item(record: PaperRecord) -> str:
    paper = record.data
    links = format_links(paper)
    tags = format_tags(paper)
    link_text = f" {links}" if links else ""
    return (
        f"- **{markdown_escape(paper['title'])}**\n"
        f"  {tags}\n"
        f"  {markdown_escape(paper['one_liner'])}{link_text}"
    )
