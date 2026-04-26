from __future__ import annotations

import json
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path
from typing import Any

from paperlib import TAG_GROUPS, load_papers, load_taxonomy, normalize_key


FORM_HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
URL_RE = re.compile(r"https?://[^\s<>()]+")
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
EMPTY_VALUES = {"", "_No response_", "No response"}
DEFAULT_TAGS = {
    "topics": ["enzyme-design"],
    "methods": ["hybrid-computational"],
    "evidence": ["computational-only"],
    "applications": ["general"],
}
BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata",
}
BLOCKED_HOST_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
)
SAFE_PORTS = {80, 443}


def load_event(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def issue_from_event(event: dict[str, Any]) -> dict[str, Any]:
    issue = event.get("issue")
    if not isinstance(issue, dict):
        raise ValueError("GitHub event does not contain an issue payload")
    return issue


def issue_labels(issue: dict[str, Any]) -> set[str]:
    labels = issue.get("labels", [])
    names: set[str] = set()
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, dict) and label.get("name"):
                names.add(str(label["name"]))
            elif isinstance(label, str):
                names.add(label)
    return names


def parse_issue_form_body(body: str | None) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in (body or "").splitlines():
        match = FORM_HEADING_RE.match(line.strip())
        if match:
            current = normalize_form_key(match.group(1))
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    parsed: dict[str, str] = {}
    for key, lines in sections.items():
        value = "\n".join(lines).strip()
        if value not in EMPTY_VALUES:
            parsed[key] = value
    return parsed


def suggestion_from_issue(issue: dict[str, Any]) -> dict[str, Any]:
    form = parse_issue_form_body(str(issue.get("body") or ""))
    title_hint = clean_issue_title(str(issue.get("title") or ""))
    body = str(issue.get("body") or "")
    url = first_matching_field(form, ("paper url", "url", "doi arxiv biorxiv pubmed or publisher url"))
    if not url:
        url = extract_first_url(body + "\n" + title_hint)
    note = first_matching_field(form, ("note", "why", "why this paper matters", "why is it relevant", "relevance"))
    tags = first_matching_field(form, ("tags", "suggested tags"))
    code = first_matching_field(form, ("code", "code or project link", "project", "dataset"))
    title = first_matching_field(form, ("paper title", "title")) or title_hint
    return {
        "issue": issue.get("number"),
        "title": title,
        "url": clean_url(url),
        "note": note,
        "suggested_tags": tags,
        "code": clean_url(code),
        "submitted_by": (issue.get("user") or {}).get("login", ""),
    }


def first_matching_field(form: dict[str, str], candidates: tuple[str, ...]) -> str:
    for candidate in candidates:
        key = normalize_form_key(candidate)
        if key in form:
            return form[key].strip()
    for key, value in form.items():
        if any(candidate in key for candidate in candidates):
            return value.strip()
    return ""


def normalize_form_key(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def clean_issue_title(title: str) -> str:
    value = re.sub(r"^\s*\[?paper\]?\s*:?\s*", "", title, flags=re.IGNORECASE).strip()
    return "" if value.lower() in {"paper", "paper suggestion"} else value


def extract_first_url(text: str) -> str:
    match = URL_RE.search(text or "")
    return clean_url(match.group(0)) if match else ""


def clean_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    match = URL_RE.search(value)
    if not match:
        return ""
    return match.group(0).rstrip(".,);]")


def is_safe_public_url(value: Any, resolve: bool = False) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urllib.parse.urlparse(value.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.hostname:
        return False
    hostname = parsed.hostname.strip().lower().rstrip(".")
    if hostname in BLOCKED_HOSTS or any(hostname.endswith(suffix) for suffix in BLOCKED_HOST_SUFFIXES):
        return False
    try:
        if parsed.port is not None and parsed.port not in SAFE_PORTS:
            return False
    except ValueError:
        return False
    if is_blocked_ip(hostname):
        return False
    if resolve:
        try:
            addresses = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except socket.gaierror:
            return False
        for address in addresses:
            if is_blocked_ip(address[4][0]):
                return False
    return True


def is_blocked_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def enrich_metadata(url: str, title_hint: str = "", fetch: bool = False) -> dict[str, Any]:
    metadata = infer_url_metadata(url)
    if title_hint and not metadata.get("title"):
        metadata["title"] = title_hint
    if fetch:
        fetched = fetch_metadata(url, metadata)
        metadata.update({key: value for key, value in fetched.items() if value not in (None, "", [])})
    return metadata


def infer_url_metadata(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    doi = extract_doi(url)
    arxiv_id = extract_arxiv_id(url)
    pubmed_id = extract_pubmed_id(url)
    source = source_from_host(host, doi=doi, arxiv_id=arxiv_id, pubmed_id=pubmed_id)
    if source in {"biorxiv", "medrxiv"} and doi:
        doi = normalize_preprint_doi(doi)
    metadata: dict[str, Any] = {
        "title": "",
        "authors": [],
        "year": None,
        "date": "",
        "source": source,
        "doi": doi,
        "url": url,
        "pdf": "",
        "code": "",
        "project": "",
        "preprint_url": url if source in {"arxiv", "biorxiv", "medrxiv"} else "",
        "published_url": "" if source in {"arxiv", "biorxiv", "medrxiv"} else url,
        "identifier": "",
    }
    if arxiv_id:
        metadata["identifier"] = "arxiv-" + slugify(arxiv_id)
        metadata["pdf"] = f"https://arxiv.org/pdf/{arxiv_id}"
    elif doi:
        metadata["identifier"] = "doi-" + slugify(doi)
    elif pubmed_id:
        metadata["identifier"] = f"pubmed-{pubmed_id}"
    return metadata


def fetch_metadata(url: str, metadata: dict[str, Any]) -> dict[str, Any]:
    try:
        if not is_safe_public_url(url):
            return {}
        if metadata.get("source") in {"biorxiv", "medrxiv"} and metadata.get("doi"):
            fetched = fetch_biorxiv_metadata(str(metadata["doi"]), str(metadata["source"]))
            if fetched:
                return fetched
        if metadata.get("doi"):
            fetched = fetch_crossref_metadata(str(metadata["doi"]))
            if fetched:
                return fetched
        arxiv_id = extract_arxiv_id(url)
        if arxiv_id:
            return fetch_arxiv_metadata(arxiv_id)
        pubmed_id = extract_pubmed_id(url)
        if pubmed_id:
            return fetch_pubmed_metadata(pubmed_id)
        return fetch_html_metadata(url)
    except (urllib.error.URLError, TimeoutError, ValueError, ET.ParseError, json.JSONDecodeError):
        return {}


def fetch_biorxiv_metadata(doi: str, server: str) -> dict[str, Any]:
    clean_doi = normalize_preprint_doi(doi)
    encoded = urllib.parse.quote(clean_doi, safe="/")
    data = fetch_json(f"https://api.biorxiv.org/details/{server}/{encoded}/na/json")
    collection = data.get("collection", [])
    if not collection:
        return {}
    item = collection[-1]
    version = str(item.get("version") or "").strip()
    version_suffix = f"v{version}" if version else ""
    preprint_url = f"https://www.{server}.org/content/{clean_doi}{version_suffix}"
    pdf_url = f"{preprint_url}.full.pdf" if version_suffix else ""
    authors = split_preprint_authors(str(item.get("authors") or ""))
    date_value = str(item.get("date") or "")
    return {
        "title": str(item.get("title") or "").strip(),
        "authors": authors,
        "year": int(date_value[:4]) if re.match(r"^\d{4}", date_value) else None,
        "date": date_value if re.match(r"^\d{4}-\d{2}-\d{2}$", date_value) else "",
        "source": server,
        "doi": clean_doi,
        "preprint_url": preprint_url,
        "pdf": pdf_url,
        "abstract": str(item.get("abstract") or "").strip(),
        "identifier": "doi-" + slugify(clean_doi),
    }


def fetch_crossref_metadata(doi: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(doi, safe="")
    data = fetch_json(f"https://api.crossref.org/works/{encoded}")
    message = data.get("message", {})
    date_value = date_from_crossref(message) or ""
    authors = []
    for author in message.get("author", [])[:20]:
        if isinstance(author, dict):
            name = " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part).strip()
            if name:
                authors.append(name)
    return {
        "title": first_list_item(message.get("title")),
        "authors": authors,
        "year": int(date_value[:4]) if date_value else None,
        "date": date_value,
        "source": first_list_item(message.get("container-title")) or "doi",
        "doi": doi,
        "published_url": message.get("URL", ""),
    }


def fetch_arxiv_metadata(arxiv_id: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(arxiv_id, safe="")
    raw = fetch_bytes(f"https://export.arxiv.org/api/query?id_list={encoded}", limit=200_000)
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entry = root.find("atom:entry", ns)
    if entry is None:
        return {}
    title = text_of(entry.find("atom:title", ns))
    published = text_of(entry.find("atom:published", ns))
    authors = [text_of(node.find("atom:name", ns)) for node in entry.findall("atom:author", ns)]
    authors = [author for author in authors if author]
    date_value = published[:10] if published else ""
    return {
        "title": normalize_spaces(title),
        "authors": authors,
        "year": int(date_value[:4]) if date_value else None,
        "date": date_value,
        "source": "arxiv",
        "preprint_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
    }


def fetch_pubmed_metadata(pubmed_id: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"db": "pubmed", "id": pubmed_id, "retmode": "json"})
    data = fetch_json(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?{query}")
    record = data.get("result", {}).get(pubmed_id, {})
    date_value = parse_pubmed_date(str(record.get("pubdate", "")))
    authors = [item.get("name", "") for item in record.get("authors", []) if isinstance(item, dict)]
    return {
        "title": str(record.get("title", "")).rstrip("."),
        "authors": [author for author in authors if author],
        "year": int(date_value[:4]) if date_value else None,
        "date": date_value,
        "source": str(record.get("source") or "pubmed"),
    }


def fetch_html_metadata(url: str) -> dict[str, Any]:
    html = fetch_bytes(url, limit=300_000).decode("utf-8", errors="ignore")
    title = html_meta(html, ("citation_title", "dc.title", "og:title")) or html_title(html)
    authors = html_meta_all(html, ("citation_author", "dc.creator"))
    date_value = html_meta(html, ("citation_publication_date", "citation_online_date", "article:published_time", "dc.date"))[:10]
    doi = html_meta(html, ("citation_doi",)) or extract_doi(html)
    return {
        "title": normalize_spaces(title),
        "authors": authors,
        "year": int(date_value[:4]) if re.match(r"^\d{4}", date_value) else None,
        "date": date_value if re.match(r"^\d{4}-\d{2}-\d{2}$", date_value) else "",
        "doi": doi,
    }


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def fetch_bytes(url: str, limit: int = 1_000_000, redirect_limit: int = 5) -> bytes:
    if redirect_limit < 0:
        raise ValueError("too many redirects")
    if not is_safe_public_url(url, resolve=True):
        raise ValueError(f"unsafe or non-public URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "enzyme-ai-papers/1.0"})
    opener = urllib.request.build_opener(NoRedirectHandler)
    try:
        with opener.open(request, timeout=12) as response:
            return response.read(limit)
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            location = exc.headers.get("Location")
            if not location:
                raise
            return fetch_bytes(urllib.parse.urljoin(url, location), limit=limit, redirect_limit=redirect_limit - 1)
        raise


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def extract_doi(text: str) -> str:
    match = DOI_RE.search(text or "")
    return match.group(0).rstrip(".,);]").lower() if match else ""


def normalize_preprint_doi(doi: str) -> str:
    return re.sub(r"v\d+$", "", doi.strip().lower())


def split_preprint_authors(value: str) -> list[str]:
    if not value.strip():
        return []
    return [normalize_spaces(author) for author in value.split(";") if normalize_spaces(author)]


def extract_arxiv_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if "arxiv.org" not in parsed.netloc.lower():
        return ""
    match = re.search(r"/(?:abs|pdf)/([^/?#]+)", parsed.path)
    if not match:
        return ""
    return match.group(1).removesuffix(".pdf")


def extract_pubmed_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if "pubmed.ncbi.nlm.nih.gov" not in parsed.netloc.lower():
        return ""
    match = re.search(r"/(\d+)/?", parsed.path)
    return match.group(1) if match else ""


def source_from_host(host: str, doi: str = "", arxiv_id: str = "", pubmed_id: str = "") -> str:
    if arxiv_id:
        return "arxiv"
    if "biorxiv.org" in host:
        return "biorxiv"
    if "medrxiv.org" in host:
        return "medrxiv"
    if pubmed_id:
        return "pubmed"
    if doi or "doi.org" in host:
        return "doi"
    return host.split(".")[0] if host else "unknown"


def infer_tags(text: str, explicit_tags: str = "") -> dict[str, list[str]]:
    taxonomy = load_taxonomy()
    lower_text = f"{explicit_tags}\n{text}".lower()
    result: dict[str, list[str]] = {}
    for group in TAG_GROUPS:
        result[group] = []
        for tag, meta in taxonomy[group].items():
            terms = {tag, tag.replace("-", " ")}
            if isinstance(meta, dict):
                terms.add(str(meta.get("label", "")).lower())
                terms.update(str(alias).lower() for alias in meta.get("aliases", []))
            if any(term and term in lower_text for term in terms):
                result[group].append(tag)
        if not result[group]:
            result[group] = list(DEFAULT_TAGS[group])
    return result


def find_existing(candidate: dict[str, Any]) -> Any | None:
    target_issue = candidate.get("issue")
    target_doi = normalize_key(candidate.get("doi", ""))
    target_title = normalize_key(candidate.get("title", ""))
    target_url = normalize_url(candidate.get("url", ""))
    for record in load_papers():
        curation = record.data.get("curation", {})
        issue = record.data.get("issue") or (curation.get("issue") if isinstance(curation, dict) else None)
        if target_issue and issue == target_issue:
            return record
        if target_doi and normalize_key(record.data.get("doi", "")) == target_doi:
            return record
        if target_url and normalize_url(record.data.get("url", "")) == target_url:
            return record
        if target_title and normalize_key(record.data.get("title", "")) == target_title:
            return record
    return None


def normalize_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    parsed = urllib.parse.urlparse(value.strip())
    return urllib.parse.urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", parsed.query, ""))


def make_paper_id(metadata: dict[str, Any], issue_number: Any, year: int) -> str:
    identifier = str(metadata.get("identifier") or "").strip("-")
    if identifier:
        return slugify(identifier)
    title = str(metadata.get("title") or "").strip()
    if title:
        return f"{year}-{slugify(title)[:70].strip('-')}"
    return f"issue-{issue_number}"


def unique_paper_id(base_id: str, issue_number: Any) -> str:
    existing = {record.paper_id for record in load_papers()}
    if base_id not in existing:
        return base_id
    candidate = f"{base_id}-issue-{issue_number}"
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}-{index}" in existing:
        index += 1
    return f"{candidate}-{index}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-+", "-", slug) or "paper"


def first_list_item(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return str(value or "")


def date_from_crossref(message: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued"):
        parts = (((message.get(key) or {}).get("date-parts") or [[]])[0])
        if parts:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def parse_pubmed_date(value: str) -> str:
    match = re.search(r"(\d{4})(?:\s+([A-Za-z]{3}))?(?:\s+(\d{1,2}))?", value)
    if not match:
        return ""
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    month = months.get((match.group(2) or "").lower(), 1)
    day = int(match.group(3) or 1)
    return f"{int(match.group(1)):04d}-{month:02d}-{day:02d}"


def html_meta(html: str, names: tuple[str, ...]) -> str:
    values = html_meta_all(html, names)
    return values[0] if values else ""


def html_meta_all(html: str, names: tuple[str, ...]) -> list[str]:
    results: list[str] = []
    for name in names:
        pattern = re.compile(
            rf'<meta\s+[^>]*(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )
        results.extend(normalize_spaces(unescape(match.group(1))) for match in pattern.finditer(html))
    return [value for value in results if value]


def html_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    return normalize_spaces(unescape(match.group(1))) if match else ""


def text_of(node: ET.Element | None) -> str:
    return normalize_spaces(node.text or "") if node is not None else ""


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()
