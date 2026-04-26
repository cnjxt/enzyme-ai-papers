# Deployment Guide

This guide explains how to publish this project as a GitHub-hosted paper
sharing and weekly digest platform.

## What Gets Deployed

The project has two public surfaces:

- GitHub repository: stores issues, curation pull requests, YAML paper records,
  and GitHub Actions.
- GitHub Pages website: serves the generated MkDocs site from `docs/`.

The normal flow after deployment is:

```text
User submits URL -> GitHub issue preview -> maintainer label -> generated PR -> merge -> website updates
```

## 1. Create the GitHub Repository

Create a new GitHub repository, for example:

```text
enzyme-ai-papers
```

Then push the local project:

```bash
git init
git add .
git commit -m "Initial enzyme AI papers platform"
git branch -M main
git remote add origin https://github.com/<owner>/enzyme-ai-papers.git
git push -u origin main
```

Purpose: this gives GitHub Actions, Issues, Pull Requests, and Pages a real
repository to operate on.

## 2. Configure Public URLs

Update `mkdocs.yml`:

```yaml
site_url: https://<owner>.github.io/enzyme-ai-papers/
repo_url: https://github.com/<owner>/enzyme-ai-papers
repo_name: <owner>/enzyme-ai-papers
```

Then regenerate the site:

```bash
python3 scripts/build_docs.py
git add mkdocs.yml README.md docs/
git commit -m "Configure public repository URLs"
git push
```

Purpose: the Submit page uses `repo_url` to open GitHub issues. If this remains
`your-org/enzyme-ai-papers`, users will be sent to the wrong repository.

## 3. Enable GitHub Issues

In GitHub:

```text
Settings -> Features -> Issues
```

Enable Issues.

Purpose: user paper suggestions are stored as GitHub issues. The issue template
at `.github/ISSUE_TEMPLATE/paper_suggestion.yml` provides the URL-first form.

## 4. Create Curation Labels

Create these labels in the repository:

```text
needs-review
paper-suggestion
accepted
featured
needs-info
rejected
automated-curation
```

Purpose:

- `needs-review`: default state for new suggestions.
- `paper-suggestion`: identifies issues created from the paper template.
- `accepted`: maintainer decision to include the paper.
- `featured`: marks a paper as a Pick of the Week candidate.
- `needs-info`: asks the submitter for more context.
- `rejected`: declines and closes the suggestion.
- `automated-curation`: marks pull requests created by automation.

## 5. Enable GitHub Actions Write Permissions

In GitHub:

```text
Settings -> Actions -> General -> Workflow permissions
```

Select:

```text
Read and write permissions
Allow GitHub Actions to create and approve pull requests
```

Purpose: the issue curation workflow needs permission to comment on issues,
write generated files to a branch, and open pull requests.

## 6. Configure GitHub Pages

The simplest setup is:

```text
Settings -> Pages
Build and deployment: Deploy from a branch
Branch: main
Folder: /docs
```

Purpose: `scripts/build_docs.py` generates the website under `docs/`, so GitHub
Pages can publish it directly after PRs are merged.

## 7. Protect the Main Branch

Recommended branch protection for `main`:

- Require pull request before merging.
- Require status checks to pass.
- Require the `Validate` workflow.
- Require the `Build static site` workflow.
- Do not allow direct pushes except for trusted maintainers if needed.

Purpose: issue automation creates pull requests, but maintainers still review
and merge. This keeps public submissions from directly changing the archive.

## 8. Understand the Workflows

### Issue Curation

File:

```text
.github/workflows/issue-curation.yml
```

When an issue is opened, edited, or reopened, it runs:

```bash
python scripts/preview_issue.py --event "$GITHUB_EVENT_PATH" --fetch-metadata
```

It comments a metadata preview on the issue.

When a maintainer applies `accepted` or `featured`, it runs:

```bash
python scripts/accept_issue.py --event "$GITHUB_EVENT_PATH" --reviewer "$GITHUB_ACTOR" --fetch-metadata
python scripts/build_docs.py
python scripts/validate_papers.py
python -m unittest discover -s tests
```

Then it opens a curation pull request.

### Validation

File:

```text
.github/workflows/validate.yml
```

Runs on pull requests and pushes to `main`. It validates metadata, regenerates
docs, runs tests, and checks that generated files are committed.

### Static Site Build

File:

```text
.github/workflows/build-site.yml
```

Runs MkDocs in strict mode to catch broken pages, links, and build errors.

## 9. End-to-End Acceptance Test

After deployment, test the real workflow:

1. Open the website Submit page.
2. Submit a public paper URL.
3. Confirm a GitHub issue is created.
4. Confirm the preview comment appears.
5. Add the `accepted` label as a maintainer.
6. Confirm a pull request is created.
7. Review the generated YAML under `data/papers/YYYY/`.
8. Confirm `README.md` and `docs/` include the paper.
9. Merge the PR.
10. Confirm GitHub Pages updates.

Purpose: this verifies the real repository permissions, issue template,
metadata fetch, generated PR, validation, and Pages publication.

## 10. Release Checklist

Before announcing the project publicly:

- Replace or remove example seed papers.
- Confirm `mkdocs.yml` uses the real repository and Pages URL.
- Confirm all curation labels exist.
- Confirm GitHub Actions can open pull requests.
- Confirm branch protection is enabled.
- Confirm GitHub Pages serves the `docs/` site.
- Confirm one real paper suggestion can complete the full issue-to-PR flow.

## Operational Notes

- Metadata lookup is best-effort. Maintainers should review generated YAML.
- The website Submit form contains no GitHub token and cannot write accepted
  data directly.
- Localhost, private IP, `.local`, and non-standard-port URLs are rejected by
  the curation scripts before metadata lookup.
- Weekly digests are generated from `accepted_at`; maintainers do not need to
  write week IDs manually.
