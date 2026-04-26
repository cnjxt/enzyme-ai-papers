from __future__ import annotations

import html
import shutil
import sys
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from paperlib import (
    DOCS_DIR,
    ROOT,
    TAG_GROUPS,
    compact_paper_item,
    index_papers,
    iso_week,
    load_taxonomy,
    load_yaml,
    load_papers,
    load_weeklies,
    parse_record_date,
    sorted_papers,
    taxonomy_labels,
    validate_all,
    write_text,
)


PROJECT_DESCRIPTION = (
    "A curated weekly digest of AI and computational papers for enzyme design, "
    "engineering, function prediction, and biocatalysis."
)
SITE_TITLE = "Enzyme AI Papers"
GENERATED = "<!-- AUTO-GENERATED. DO NOT EDIT DIRECTLY. -->\n\n"
PAGE_PREFIX = "---\nhide:\n  - navigation\n  - toc\n---\n\n" + GENERATED


def main() -> int:
    errors = validate_all()
    if errors:
        print("Cannot build MkDocs pages because validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    papers = sorted_papers(load_papers())
    paper_index = index_papers(papers)
    weeklies = derive_weeklies(papers, paper_index)
    latest = weeklies[0] if weeklies else None

    build_readme(weeklies, paper_index)
    clean_docs_dir()
    build_home_page(latest, paper_index, papers)
    build_archive_page(papers, paper_index, weeklies, latest)
    build_info_page(latest)
    build_assets()

    print("MkDocs pages and README generated.")
    return 0


def clean_docs_dir() -> None:
    shutil.rmtree(DOCS_DIR, ignore_errors=True)
    (DOCS_DIR / "assets").mkdir(parents=True, exist_ok=True)


def build_readme(weeklies: list[dict[str, Any]], paper_index: dict[str, Any]) -> None:
    lines = [
        "# Enzyme AI Papers",
        "",
        PROJECT_DESCRIPTION,
        "URL-first, curator-reviewed, and designed for quick reading.",
        "",
    ]

    latest = weeklies[0] if weeklies else None
    if latest is None:
        lines.extend(["## This Week", "", "No weekly digest has been published yet.", ""])
    else:
        append_readme_week(lines, latest, paper_index, readme_week_label(latest, 0))
        if len(weeklies) > 1:
            append_readme_week(lines, weeklies[1], paper_index, readme_week_label(weeklies[1], 1))

    lines.extend(
        [
            "## More Information",
            "",
            "- Website source: `docs/`",
            "- Submit a paper by opening an issue with a paper URL.",
            "- Maintainers accept papers by applying the `accepted` label.",
            "- How to read, submit, and maintain the project: [MORE_INFO.md](MORE_INFO.md)",
            "- How to deploy a public instance: [DEPLOYMENT.md](DEPLOYMENT.md)",
            "- Step-by-step deployment and submission runbook: [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)",
            "- Curation rules: [CURATION.md](CURATION.md)",
            "- Contribution workflow: [CONTRIBUTING.md](CONTRIBUTING.md)",
            "",
        ]
    )

    write_text(ROOT / "README.md", "\n".join(lines).rstrip() + "\n")


def append_readme_week(
    lines: list[str],
    weekly: dict[str, Any],
    paper_index: dict[str, Any],
    label: str,
) -> None:
    commentary = weekly.get("commentary", {})
    pick = paper_index[weekly["pick_of_the_week"]]

    lines.extend(
        [
            f"## {label}: {weekly['title']} ({weekly['date_range']})",
            "",
            weekly["summary"],
            "",
            "### Pick of the Week",
            "",
            compact_paper_item(pick),
            "",
            f"> {commentary.get(pick.paper_id, pick.data['why_it_matters'])}",
            "",
            "### Papers",
            "",
        ]
    )

    for section in weekly["sections"].values():
        lines.append(f"#### {section['title']}")
        lines.append("")
        for paper_id in section["papers"]:
            lines.append(compact_paper_item(paper_index[paper_id]))
        lines.append("")


def build_home_page(latest: dict[str, Any] | None, paper_index: dict[str, Any], papers: list[Any]) -> None:
    if latest is None:
        issue = None
        main_content = """
<section class="empty-state">
  <h2>No weekly issue yet</h2>
  <p>Accept a paper suggestion issue to publish the first automatically generated weekly digest.</p>
</section>
"""
    else:
        weekly = latest
        issue = weekly
        main_content = render_weekly(weekly, paper_index)

    content = f"""{PAGE_PREFIX}{render_page_shell("weekly", issue)}

{render_toolbar(papers)}

{main_content}
"""
    write_text(DOCS_DIR / "index.md", content)


def render_weekly(weekly: dict[str, Any], paper_index: dict[str, Any]) -> str:
    commentary = weekly.get("commentary", {})
    pick = paper_index[weekly["pick_of_the_week"]]

    chunks: list[str] = [
        f"""
<section class="weekly-overview">
  <div class="section-label">{escape(readme_week_label(weekly, 0))}</div>
  <h2>{escape(weekly['title'])}</h2>
  <p class="weekly-range">{escape(weekly['week'])}: {escape(weekly['date_range'])}</p>
  <p class="weekly-summary">{escape(weekly['summary'])}</p>
</section>

<section class="pick" id="weekly-papers">
  <div class="section-label">Pick of the Week</div>
  {render_paper_card(pick, commentary.get(pick.paper_id), featured=True)}
</section>

<section class="paper-sections">
"""
    ]

    for section in weekly["sections"].values():
        cards = "\n".join(render_paper_card(paper_index[paper_id]) for paper_id in section["papers"])
        chunks.append(
            f"""
  <section class="paper-group">
    <div class="section-label">{escape(section['title'])}</div>
    <div class="paper-grid">
      {cards}
    </div>
  </section>
"""
        )

    chunks.append("</section>")
    return "\n".join(chunks)


def build_archive_page(
    papers: list[Any],
    paper_index: dict[str, Any],
    weeklies: list[dict[str, Any]],
    latest: dict[str, Any] | None,
) -> None:
    by_year: dict[int, list[Any]] = defaultdict(list)
    for paper in papers:
        by_year[paper.year].append(paper)

    groups: list[str] = []
    for year in sorted(by_year.keys(), reverse=True):
        cards = "\n".join(render_paper_card(record) for record in by_year[year])
        groups.append(
            f"""
<section class="paper-group">
  <div class="section-label">{year}</div>
  <div class="paper-grid">
    {cards}
  </div>
</section>
"""
        )

    content = f"""{PAGE_PREFIX}{render_page_shell("archive", latest)}

{render_toolbar(papers)}

{render_weekly_history(weeklies)}

{render_weekly_archive(weeklies, paper_index)}

{''.join(groups) if groups else '<section class="empty-state"><h2>No papers yet</h2></section>'}
"""
    write_text(DOCS_DIR / "archive.md", content)


def build_info_page(issue: dict[str, Any] | None) -> None:
    issue_url = issue_submission_url()
    content = f"""{PAGE_PREFIX}{render_page_shell("submit", issue)}

{render_submit_form(issue_url)}

<section class="info-grid">
  <article class="info-block">
    <h2>Readers</h2>
    <p>Start with the latest weekly issue. Use the archive when you want to browse by tag or keyword.</p>
  </article>
  <article class="info-block">
    <h2>Submitters</h2>
    <p>Open a GitHub issue with a paper URL. Notes, tags, title, code, and project links are optional.</p>
  </article>
  <article class="info-block">
    <h2>Maintainers</h2>
    <p>Review the issue preview, add <code>accepted</code> to include it, and add <code>featured</code> for a weekly pick.</p>
  </article>
</section>

<section class="command-block">
  <h2>Automation</h2>
  <pre><code>Issue opened -> metadata preview
Label accepted -> paper YAML draft + generated weekly digest
Label featured -> Pick of the Week candidate
Pull request -> validation + MkDocs build</code></pre>
</section>
"""
    write_text(DOCS_DIR / "info.md", content)


def render_submit_form(issue_url: str) -> str:
    return f"""
<section class="submit-panel">
  <form id="paper-submit-form" class="submit-form" data-issue-url="{escape(issue_url)}">
    <div>
      <div class="section-label">Submit paper</div>
      <h2>Share a paper URL</h2>
    </div>
    <label for="submit-paper-url">Paper URL</label>
    <input id="submit-paper-url" name="url" type="url" required placeholder="https://doi.org/...">
    <label for="submit-paper-title">Title</label>
    <input id="submit-paper-title" name="title" type="text" placeholder="Optional">
    <label for="submit-paper-note">Why this paper matters</label>
    <textarea id="submit-paper-note" name="note" rows="4" placeholder="Optional"></textarea>
    <label for="submit-paper-tags">Tags</label>
    <input id="submit-paper-tags" name="tags" type="text" placeholder="enzyme design, PLM, wet lab validation">
    <label for="submit-paper-code">Code or project link</label>
    <input id="submit-paper-code" name="code" type="url" placeholder="https://github.com/...">
    <div class="submit-actions">
      <button type="submit">Open GitHub Submission</button>
      <a href="{escape(issue_url)}">Open blank issue</a>
    </div>
    <p id="submit-form-status" class="form-status" aria-live="polite"></p>
  </form>
  <aside class="review-boundary">
    <div class="section-label">Review boundary</div>
    <ul>
      <li>Submissions open as GitHub issues under the submitter account.</li>
      <li>The website does not store a GitHub token or write repository data.</li>
      <li>Only maintainers can apply curation labels such as <code>accepted</code>.</li>
      <li>Accepted papers are generated through a pull request and validation checks.</li>
    </ul>
  </aside>
</section>
"""


def issue_submission_url() -> str:
    config = load_yaml(ROOT / "mkdocs.yml")
    repo_url = ""
    if isinstance(config, dict):
        repo_url = str(config.get("repo_url") or "").rstrip("/")
    if not repo_url:
        repo_url = "https://github.com/your-org/enzyme-ai-papers"
    return f"{repo_url}/issues/new"


def derive_weeklies(papers: list[Any], paper_index: dict[str, Any]) -> list[dict[str, Any]]:
    taxonomy = load_taxonomy()
    topic_labels = taxonomy_labels(taxonomy, "topics")
    overrides = {record.week: record.data for record in load_weeklies()}
    by_week: dict[str, list[Any]] = defaultdict(list)
    for paper in papers:
        by_week[paper.week].append(paper)

    weeklies: list[dict[str, Any]] = []
    for week, records in by_week.items():
        sorted_records = sorted_papers(records)
        override = overrides.get(week, {})
        pick = override.get("pick_of_the_week") if isinstance(override, dict) else None
        if not pick or pick not in paper_index:
            pick = next((record.paper_id for record in sorted_records if record.featured), sorted_records[0].paper_id)

        generated_sections = auto_sections(sorted_records, topic_labels)
        sections = override.get("sections") if isinstance(override, dict) else None
        if sections:
            sections = merge_sections(sections, generated_sections)
        else:
            sections = generated_sections

        commentary = override.get("commentary", {}) if isinstance(override, dict) else {}
        latest_date = max(parse_record_date(record.accepted_at) for record in sorted_records).isoformat()
        week_start, week_end = iso_week_bounds(week)
        weeklies.append(
            {
                "week": week,
                "title": override.get("title", f"Enzyme AI Papers Weekly - {week}") if isinstance(override, dict) else f"Enzyme AI Papers Weekly - {week}",
                "date": override.get("date", latest_date) if isinstance(override, dict) else latest_date,
                "start_date": week_start.isoformat(),
                "end_date": week_end.isoformat(),
                "date_range": format_week_range(week),
                "summary": override.get("summary", auto_summary(week, sorted_records)) if isinstance(override, dict) else auto_summary(week, sorted_records),
                "pick_of_the_week": pick,
                "sections": sections,
                "commentary": commentary if isinstance(commentary, dict) else {},
            }
        )

    return sorted(weeklies, key=lambda record: record["week"], reverse=True)


def auto_sections(records: list[Any], topic_labels: dict[str, str]) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for record in records:
        topics = record.data.get("topics", [])
        topic = str(topics[0]) if topics else "general"
        if topic not in sections:
            sections[topic] = {
                "title": topic_labels.get(topic, titleize_tag(topic)),
                "papers": [],
            }
        sections[topic]["papers"].append(record.paper_id)
    return sections


def merge_sections(
    override_sections: dict[str, Any],
    generated_sections: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    included: set[str] = set()
    for section_id, section in override_sections.items():
        if not isinstance(section, dict):
            continue
        papers = [str(paper_id) for paper_id in section.get("papers", [])]
        included.update(papers)
        merged[str(section_id)] = {
            "title": section.get("title") or generated_sections.get(section_id, {}).get("title") or titleize_tag(str(section_id)),
            "papers": papers,
        }

    for section_id, section in generated_sections.items():
        missing = [paper_id for paper_id in section["papers"] if paper_id not in included]
        if not missing:
            continue
        if section_id in merged:
            merged[section_id]["papers"].extend(missing)
        else:
            merged[section_id] = {
                "title": section["title"],
                "papers": missing,
            }
        included.update(missing)
    return merged


def auto_summary(week: str, records: list[Any]) -> str:
    count = len(records)
    noun = "paper" if count == 1 else "papers"
    return f"{count} accepted enzyme AI or computational enzyme {noun} collected for {week}."


def iso_week_bounds(week: str) -> tuple[date, date]:
    match = week.split("-W", 1)
    if len(match) != 2:
        raise ValueError(f"invalid ISO week: {week}")
    start = date.fromisocalendar(int(match[0]), int(match[1]), 1)
    return start, start + timedelta(days=6)


def format_week_range(week: str) -> str:
    start, end = iso_week_bounds(week)
    if start <= date.today() <= end:
        return f"{format_dot_date(start)}-"
    if start.year == end.year:
        return f"{format_dot_date(start)}-{end.month}.{end.day}"
    return f"{format_dot_date(start)}-{format_dot_date(end)}"


def format_dot_date(value: date) -> str:
    return f"{value.year}.{value.month}.{value.day}"


def readme_week_label(weekly: dict[str, Any], index: int) -> str:
    current_week = iso_week(date.today().isoformat())
    last_week = iso_week((date.today() - timedelta(days=7)).isoformat())
    if index == 0 and weekly["week"] == current_week:
        return "This Week"
    if index == 1 and weekly["week"] == last_week:
        return "Last Week"
    return "Latest Week" if index == 0 else "Previous Week"


def render_weekly_history(weeklies: list[dict[str, Any]]) -> str:
    if not weeklies:
        return ""
    links = "\n".join(
        f'<a class="weekly-link" href="#week-{escape(weekly["week"])}"><strong>{escape(weekly["week"])}</strong><span>{escape(str(weekly["date_range"]))}</span></a>'
        for weekly in weeklies
    )
    return f"""
<section class="weekly-history">
  <div class="section-label">Weekly issues</div>
  <div class="weekly-links">
    {links}
  </div>
</section>
"""


def render_weekly_archive(weeklies: list[dict[str, Any]], paper_index: dict[str, Any]) -> str:
    if not weeklies:
        return ""
    chunks = ['<section class="paper-sections weekly-archive">']
    for weekly in weeklies:
        commentary = weekly.get("commentary", {})
        pick = paper_index[weekly["pick_of_the_week"]]
        section_cards: list[str] = []
        for section in weekly["sections"].values():
            section_papers = [paper_id for paper_id in section["papers"] if paper_id != pick.paper_id]
            if not section_papers:
                continue
            cards = "\n".join(render_paper_card(paper_index[paper_id]) for paper_id in section_papers)
            section_cards.append(
                f"""
    <div class="paper-subgroup">
      <div class="section-label">{escape(section['title'])}</div>
      <div class="paper-grid">{cards}</div>
    </div>
"""
            )
        chunks.append(
            f"""
  <section class="paper-group" id="week-{escape(weekly['week'])}">
    <div class="section-label">{escape(weekly['week'])}: {escape(weekly['date_range'])}</div>
    <h2>{escape(weekly['title'])}</h2>
    <p class="weekly-summary">{escape(weekly['summary'])}</p>
    <div class="section-label">Pick of the Week</div>
    {render_paper_card(pick, commentary.get(pick.paper_id), featured=True)}
    {''.join(section_cards)}
  </section>
"""
        )
    chunks.append("</section>")
    return "\n".join(chunks)


def build_assets() -> None:
    write_text(DOCS_DIR / "assets" / "site.css", SITE_CSS)
    write_text(DOCS_DIR / "assets" / "app.js", SITE_JS)


def render_toolbar(papers: list[Any]) -> str:
    return f"""
<section class="paper-toolbar" aria-label="Paper filters">
  <label class="search-label" for="paper-search">Search</label>
  <input id="paper-search" type="search" placeholder="Search title, tag, note, author">
  <button class="filter-chip is-active" data-filter="all" type="button">All</button>
  {render_filter_buttons(papers)}
</section>
"""


def render_page_shell(active: str, issue: dict[str, Any] | None) -> str:
    if active == "weekly":
        links = {"weekly": "./", "archive": "archive/", "submit": "info/", "issue": "#weekly-papers"}
    elif active == "archive":
        links = {"weekly": "../", "archive": "./", "submit": "../info/", "issue": "../#weekly-papers"}
    else:
        links = {"weekly": "../", "archive": "../archive/", "submit": "./", "issue": "../#weekly-papers"}

    return f"""
<section class="paper-start">
  <nav class="paper-switcher" aria-label="Section navigation">
    {render_switch_item("weekly", "Weekly", "Curated enzyme AI papers for this week.", links["weekly"], active)}
    {render_switch_item("archive", "Archive", "Browse accepted papers by year and tag.", links["archive"], active)}
    {render_switch_item("submit", "Submit", "Recommend a paper or maintain metadata.", links["submit"], active)}
  </nav>
  {render_issue_card(issue, links["issue"])}
</section>
"""


def render_switch_item(key: str, label: str, description: str, href: str, active: str) -> str:
    classes = "switch-item is-active" if key == active else "switch-item"
    return f"""
<a class="{classes}" href="{href}">
  <span class="switch-icon">{nav_icon(key)}</span>
  <strong>{escape(label)}</strong>
</a>
"""


def render_issue_card(issue: dict[str, Any] | None, issue_href: str) -> str:
    if issue is None:
        return """
<aside class="issue-card">
  <span class="issue-kicker">Latest issue</span>
  <strong>No issue yet</strong>
  <p>Accept a paper suggestion to publish the first issue.</p>
</aside>
"""

    return f"""
<aside class="issue-card">
  <span class="issue-kicker">Latest issue</span>
  <strong>{escape(issue['week'])}</strong>
  <span class="issue-range">{escape(issue['date_range'])}</span>
</aside>
"""


def render_filter_buttons(papers: list[Any]) -> str:
    seen: list[str] = []
    for paper in papers:
        for group in TAG_GROUPS:
            for tag in paper.data.get(group, []):
                if tag not in seen:
                    seen.append(tag)
    return "\n  ".join(
        f'<button class="filter-chip" data-filter="{escape(tag)}" type="button">{escape(tag)}</button>'
        for tag in seen[:12]
    )


def render_paper_card(record: Any, commentary: str | None = None, featured: bool = False) -> str:
    paper = record.data
    tags: list[str] = []
    for group in TAG_GROUPS:
        tags.extend(str(tag) for tag in paper.get(group, []))

    authors = ", ".join(paper.get("authors", []))
    note = commentary or paper.get("why_it_matters", "")
    tag_html = "".join(f"<span>{escape(tag)}</span>" for tag in tags)
    link_html = html_links(paper)
    classes = "paper-card is-featured" if featured else "paper-card"
    searchable = " ".join([paper["title"], authors, paper["one_liner"], note, " ".join(tags)])

    return f"""
<article class="{classes}" data-tags="{escape(' '.join(tags))}" data-search="{escape(searchable.lower())}">
  <div class="paper-meta">
    <span>{escape(paper['source'])}</span>
    <span>{escape(str(paper['year']))}</span>
  </div>
  <h3>{escape(paper['title'])}</h3>
  <p class="authors">{escape(authors)}</p>
  <p>{escape(paper['one_liner'])}</p>
  <p class="why">{escape(note)}</p>
  <div class="tags">{tag_html}</div>
  <div class="paper-links">{link_html}</div>
</article>
"""


def html_links(paper: dict[str, Any]) -> str:
    items = []
    for field, label in (
        ("url", "Paper"),
        ("pdf", "PDF"),
        ("code", "Code"),
        ("project", "Project"),
    ):
        value = paper.get(field)
        if value:
            items.append(f'<a href="{escape(value)}">{link_icon(field)}<span>{label}</span></a>')
    return "".join(items)


def link_icon(field: str) -> str:
    icons = {
        "url": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/></svg>',
        "pdf": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M8.5 16h7"/></svg>',
        "code": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.8c-2.8.6-3.4-1.2-3.4-1.2-.5-1.1-1.1-1.4-1.1-1.4-.9-.6.1-.6.1-.6 1 .1 1.6 1.1 1.6 1.1.9 1.5 2.4 1.1 2.9.8.1-.7.4-1.1.7-1.4-2.2-.3-4.6-1.1-4.6-4.9 0-1.1.4-2 1.1-2.7-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.8 1a9.6 9.6 0 0 1 5.1 0c1.9-1.3 2.8-1 2.8-1 .6 1.4.2 2.4.1 2.7.7.7 1.1 1.6 1.1 2.7 0 3.8-2.3 4.6-4.6 4.9.4.3.8 1 .8 2v2.5c0 .3.2.6.8.5A10 10 0 0 0 12 2z"/></svg>',
        "project": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4z"/><path d="M4 9h16"/><path d="M8 13h3M8 16h7"/></svg>',
    }
    return icons.get(field, icons["url"])


def nav_icon(key: str) -> str:
    icons = {
        "weekly": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-3-6 3z"/><path d="M9 8h6M9 11h6"/></svg>',
        "archive": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v4H4z"/><path d="M6 9h12v10H6z"/><path d="M10 13h4"/></svg>',
        "submit": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v12"/><path d="M7 9l5-5 5 5"/><path d="M5 20h14"/></svg>',
    }
    return icons[key]


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def titleize_tag(tag: str) -> str:
    return " ".join(part.capitalize() for part in tag.split("-"))


SITE_CSS = """
:root {
  --paper-bg: #f7f7f4;
  --paper-panel: #ffffff;
  --paper-panel-soft: #f0f4ef;
  --paper-ink: #171a18;
  --paper-muted: #5f6861;
  --paper-line: #dfe5df;
  --paper-accent: #0f766e;
  --paper-accent-dark: #0b4f4a;
  --paper-warm: #b46f12;
  --paper-shadow: 0 16px 40px rgba(23, 26, 24, 0.08);
}

[data-md-color-scheme="default"] {
  --md-primary-fg-color: #0f766e;
  --md-accent-fg-color: #b46f12;
}

.md-main {
  background: var(--paper-bg);
}

.md-tabs {
  display: none;
}

.md-header {
  box-shadow: none;
}

.md-main__inner {
  margin-top: 0;
  max-width: 1180px;
}

.md-content__inner {
  margin: 0;
  padding: 0 1.2rem 3rem;
}

.md-content__inner::before {
  display: none;
}

.md-content__inner > h1:first-child {
  display: none;
}

.md-typeset h1,
.md-typeset h2,
.md-typeset h3,
.md-typeset p {
  letter-spacing: 0;
}

.paper-start {
  align-items: stretch;
  display: grid;
  gap: 0.75rem;
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 1rem 0 0.8rem;
}

.paper-switcher {
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid var(--paper-line);
  border-radius: 10px;
  display: grid;
  gap: 0.35rem;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 0.35rem;
}

.switch-item {
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--paper-ink);
  display: grid;
  gap: 0.45rem;
  grid-template-columns: 28px auto;
  justify-content: center;
  min-height: 46px;
  padding: 0.45rem 0.75rem;
  text-decoration: none;
}

.switch-item:hover {
  background: #f4f8f6;
  text-decoration: none;
}

.switch-item.is-active {
  background: var(--paper-panel);
  border-color: rgba(15, 118, 110, 0.32);
  box-shadow: var(--paper-shadow);
}

.switch-icon {
  align-items: center;
  background: #e8f3f1;
  border-radius: 7px;
  color: var(--paper-accent-dark);
  display: inline-flex;
  height: 28px;
  justify-content: center;
  width: 28px;
}

.switch-icon svg,
.paper-links svg {
  fill: none;
  height: 17px;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.8;
  width: 17px;
}

.switch-item strong {
  display: block;
  font-size: 0.88rem;
  line-height: 1.2;
}

.switch-item small {
  display: none;
  color: var(--paper-muted);
  font-size: 0.76rem;
  line-height: 1.35;
  margin-top: 0.15rem;
}

.issue-card {
  background: linear-gradient(135deg, #0f766e, #165f58);
  align-items: center;
  border-radius: 10px;
  box-shadow: var(--paper-shadow);
  color: #fff;
  display: inline-flex;
  min-height: 56px;
  padding: 0.6rem 0.9rem;
}

.issue-card strong {
  display: block;
  font-size: 1.12rem;
  line-height: 1.05;
  margin: 0;
}

.issue-range {
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.78rem;
  font-weight: 680;
  margin-left: 0.55rem;
}

.issue-card p {
  display: none;
  color: rgba(255, 255, 255, 0.82);
  font-size: 0.82rem;
  line-height: 1.4;
  margin: 0 0 0.75rem;
}

.issue-card a {
  display: none;
  color: #fff;
  font-size: 0.82rem;
  font-weight: 760;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.issue-kicker,
.paper-eyebrow,
.section-label {
  color: var(--paper-warm);
  font-size: 0.72rem;
  font-weight: 780;
  letter-spacing: 0;
  margin: 0 0 0.5rem;
  text-transform: uppercase;
}

.issue-card .issue-kicker {
  display: none;
}

.filter-chip {
  align-items: center;
  background: var(--paper-panel);
  border: 1px solid var(--paper-line);
  border-radius: 7px;
  color: var(--paper-ink);
  cursor: pointer;
  display: inline-flex;
  font-size: 0.85rem;
  font-weight: 720;
  min-height: 38px;
  padding: 0.45rem 0.75rem;
}

.filter-chip.is-active {
  background: var(--paper-accent);
  border-color: var(--paper-accent);
  color: #fff;
}

.paper-toolbar {
  align-items: center;
  background: rgba(255, 255, 255, 0.58);
  border: 1px solid var(--paper-line);
  border-radius: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin: 0 0 1.1rem;
  padding: 0.75rem;
}

.search-label {
  color: var(--paper-muted);
  font-size: 0.78rem;
  font-weight: 760;
}

#paper-search {
  background: #fff;
  border: 1px solid var(--paper-line);
  border-radius: 7px;
  color: var(--paper-ink);
  flex: 1 1 260px;
  font: inherit;
  min-height: 40px;
  min-width: 220px;
  padding: 0.45rem 0.75rem;
}

.pick {
  border-top: 1px solid var(--paper-line);
  padding: 1.4rem 0 1.5rem;
}

.weekly-overview {
  border-top: 1px solid var(--paper-line);
  padding: 1.35rem 0 1.1rem;
}

.weekly-overview h2 {
  color: var(--paper-ink);
  font-size: 1.35rem;
  line-height: 1.18;
  margin: 0 0 0.35rem;
}

.weekly-range {
  color: var(--paper-accent-dark);
  font-size: 0.9rem;
  font-weight: 760;
  margin: 0 0 0.45rem;
}

.paper-group {
  border-top: 1px solid var(--paper-line);
  padding: 1.8rem 0;
}

.weekly-history {
  border-top: 1px solid var(--paper-line);
  padding: 1.5rem 0;
}

.weekly-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.weekly-link {
  align-items: center;
  background: var(--paper-panel);
  border: 1px solid var(--paper-line);
  border-radius: 8px;
  color: var(--paper-ink);
  display: inline-flex;
  gap: 0.6rem;
  min-height: 42px;
  padding: 0.45rem 0.75rem;
  text-decoration: none;
}

.weekly-link:hover {
  background: #f4f8f6;
  text-decoration: none;
}

.weekly-link span {
  color: var(--paper-muted);
  font-size: 0.78rem;
}

.weekly-archive h2 {
  color: var(--paper-ink);
  font-size: 1.18rem;
  margin: 0 0 0.35rem;
}

.weekly-summary {
  color: var(--paper-muted);
  margin: 0 0 1rem;
}

.paper-subgroup {
  margin-top: 1rem;
}

.paper-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
}

.paper-card {
  background: var(--paper-panel);
  border: 1px solid var(--paper-line);
  border-radius: 8px;
  box-shadow: var(--paper-shadow);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  min-height: 100%;
  padding: 1rem;
}

.paper-card.is-featured {
  border-color: rgba(15, 118, 110, 0.38);
}

.paper-card[hidden] {
  display: none;
}

.paper-card h3 {
  color: var(--paper-ink);
  font-size: 1.18rem;
  line-height: 1.2;
  margin: 0;
}

.paper-card p {
  margin: 0;
}

.paper-meta,
.paper-links,
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.paper-meta span {
  color: var(--paper-muted);
  font-size: 0.78rem;
  font-weight: 680;
}

.authors {
  color: var(--paper-muted);
  font-size: 0.84rem;
}

.why {
  background: var(--paper-panel-soft);
  border-left: 3px solid var(--paper-accent);
  color: #2d3730;
  font-size: 0.86rem;
  margin-top: auto;
  padding: 0.65rem 0.75rem;
}

.tags span {
  background: #eef6f4;
  border: 1px solid #cfe3df;
  border-radius: 999px;
  color: var(--paper-accent-dark);
  font-size: 0.72rem;
  font-weight: 720;
  padding: 0.2rem 0.45rem;
}

.paper-links a {
  align-items: center;
  background: #f7fbfa;
  border: 1px solid #d8e7e4;
  border-radius: 7px;
  color: var(--paper-accent-dark);
  display: inline-flex;
  font-size: 0.86rem;
  font-weight: 760;
  gap: 0.35rem;
  min-height: 34px;
  padding: 0.32rem 0.55rem;
  text-decoration: none;
}

.paper-links a:hover {
  background: #eef6f4;
  text-decoration: none;
}

.paper-links svg {
  fill: currentColor;
  height: 16px;
  stroke-width: 1.7;
  width: 16px;
}

.info-grid {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  padding: 1.5rem 0;
}

.submit-panel {
  border-top: 1px solid var(--paper-line);
  display: grid;
  gap: 0.9rem;
  grid-template-columns: minmax(0, 1.35fr) minmax(260px, 0.65fr);
  padding: 1.4rem 0 0;
}

.submit-form,
.review-boundary {
  background: var(--paper-panel);
  border: 1px solid var(--paper-line);
  border-radius: 8px;
  padding: 1rem;
}

.submit-form {
  display: grid;
  gap: 0.65rem;
}

.submit-form h2 {
  color: var(--paper-ink);
  font-size: 1.18rem;
  line-height: 1.2;
  margin: 0;
}

.submit-form label {
  color: var(--paper-muted);
  font-size: 0.78rem;
  font-weight: 760;
}

.submit-form input,
.submit-form textarea {
  background: #fff;
  border: 1px solid var(--paper-line);
  border-radius: 7px;
  color: var(--paper-ink);
  font: inherit;
  min-height: 40px;
  padding: 0.45rem 0.65rem;
  width: 100%;
}

.submit-form textarea {
  line-height: 1.45;
  min-height: 104px;
  resize: vertical;
}

.submit-actions {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.25rem;
}

.submit-actions button,
.submit-actions a {
  align-items: center;
  border-radius: 7px;
  display: inline-flex;
  font-size: 0.88rem;
  font-weight: 760;
  min-height: 40px;
  padding: 0.45rem 0.75rem;
  text-decoration: none;
}

.submit-actions button {
  background: var(--paper-accent);
  border: 1px solid var(--paper-accent);
  color: #fff;
  cursor: pointer;
}

.submit-actions a {
  background: #f7fbfa;
  border: 1px solid #d8e7e4;
  color: var(--paper-accent-dark);
}

.form-status {
  color: var(--paper-muted);
  font-size: 0.82rem;
  margin: 0;
}

.review-boundary ul {
  margin: 0;
  padding-left: 1.1rem;
}

.review-boundary li {
  color: var(--paper-muted);
  margin: 0.35rem 0;
}

.info-block,
.command-block,
.empty-state {
  background: var(--paper-panel);
  border: 1px solid var(--paper-line);
  border-radius: 8px;
  padding: 1rem;
}

@media (max-width: 720px) {
  .paper-start {
    display: block;
  }

  .paper-switcher {
    grid-template-columns: 1fr;
  }

  .issue-card {
    margin-top: 0.85rem;
  }

  .submit-panel {
    grid-template-columns: 1fr;
  }
}
""".strip() + "\n"


SITE_JS = """
const searchInput = document.querySelector("#paper-search");
const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
const cards = Array.from(document.querySelectorAll(".paper-card"));
let activeFilter = "all";

function applyFilters() {
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
  for (const card of cards) {
    const searchText = card.dataset.search || "";
    const tags = card.dataset.tags || "";
    const matchesQuery = !query || searchText.includes(query);
    const matchesFilter = activeFilter === "all" || tags.split(" ").includes(activeFilter);
    card.hidden = !(matchesQuery && matchesFilter);
  }
}

if (searchInput) {
  searchInput.addEventListener("input", applyFilters);
}

for (const button of filterButtons) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter || "all";
    for (const item of filterButtons) {
      item.classList.toggle("is-active", item === button);
    }
    applyFilters();
  });
}

const submitForm = document.querySelector("#paper-submit-form");

function hostLabel(value) {
  try {
    return new URL(value).hostname.replace(/^www\\./, "");
  } catch (_error) {
    return "paper";
  }
}

function issueBody(fields) {
  return [
    "### Paper URL",
    "",
    fields.url,
    "",
    "### Paper title",
    "",
    fields.title || "_No response_",
    "",
    "### Why this paper matters",
    "",
    fields.note || "_No response_",
    "",
    "### Suggested tags",
    "",
    fields.tags || "_No response_",
    "",
    "### Code or project link",
    "",
    fields.code || "_No response_",
  ].join("\\n");
}

if (submitForm) {
  submitForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(submitForm);
    const fields = {
      url: String(formData.get("url") || "").trim(),
      title: String(formData.get("title") || "").trim(),
      note: String(formData.get("note") || "").trim(),
      tags: String(formData.get("tags") || "").trim(),
      code: String(formData.get("code") || "").trim(),
    };
    const status = document.querySelector("#submit-form-status");
    if (!fields.url) {
      if (status) status.textContent = "Paper URL is required.";
      return;
    }
    let target;
    try {
      target = new URL(submitForm.dataset.issueUrl || "");
    } catch (_error) {
      if (status) status.textContent = "Submission link is not configured.";
      return;
    }
    target.searchParams.set("title", `[Paper]: ${fields.title || hostLabel(fields.url)}`);
    target.searchParams.set("body", issueBody(fields));
    window.open(target.toString(), "_blank", "noopener");
    if (status) status.textContent = "Opening GitHub submission...";
  });
}
""".strip() + "\n"


if __name__ == "__main__":
    sys.exit(main())
