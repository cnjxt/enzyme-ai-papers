# More Information

Enzyme AI Papers is a lightweight paper sharing and weekly digest platform for
enzyme AI and computational enzyme research. The intended workflow is:

```text
Paper URL -> GitHub issue preview -> maintainer label -> generated archive and weekly digest
```

## How to Read

- Start with the latest weekly issue in `README.md` or the MkDocs homepage.
- Use the archive page to browse accepted papers and weekly history.
- Use tags and search on the website to narrow papers by task, method,
  evidence, or application.

## How to Submit

Use the Submit page on the website or open a paper suggestion issue and paste
the paper URL.

Everything else is optional:

- A short note about why the paper matters.
- Free-text tags.
- Code, project, dataset, or benchmark link.

The automation will comment with a review preview and suggested tags.

The website form is intentionally static. It opens a prefilled GitHub issue and
does not store credentials, call the GitHub API, or write accepted paper data.

## How to Maintain

Review the issue preview and apply labels:

- `accepted`: generate a paper record and curation pull request.
- `featured`: mark the paper as a Pick of the Week candidate.
- `needs-info`: ask for more context.
- `rejected`: decline the suggestion.

Accepted papers live under `data/papers/YYYY/`. Weekly issues are generated from
accepted paper records using `accepted_at`; `data/weekly/` is only for optional
curator overrides such as a custom summary or commentary.

Repository owners can also use the `Publish URL` GitHub Actions workflow for
trusted direct publication from a single URL. That workflow writes to `main`
and deploys Pages after running the same generation, validation, tests, and
MkDocs build steps.

## Public Project Boundary

- Visitors can submit suggestions, not accepted records.
- Maintainers control `accepted`, `featured`, `needs-info`, and `rejected`.
- Localhost, private IP, `.local`, and non-standard-port URLs are rejected by
  the curation scripts.
- The curation workflow opens a pull request instead of merging directly.

## Local Validation

```bash
python3 scripts/validate_papers.py
python3 scripts/build_docs.py
python3 -m unittest discover -s tests
```

Preview the website when MkDocs is installed:

```bash
mkdocs serve -a 127.0.0.1:8010
```

## Deployment

Use [DEPLOYMENT.md](DEPLOYMENT.md) when publishing a new GitHub-hosted instance.
It covers repository setup, public URLs, labels, Actions permissions, GitHub
Pages, branch protection, and the end-to-end acceptance test.

Use [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md) for a shorter step-by-step
execution checklist, including post-deployment paper submission and PR methods.
