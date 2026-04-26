# Curation Rules

This project is selective. The goal is to help readers find relevant enzyme AI
and computational enzyme papers quickly.

## Scope

Accepted papers should clearly relate to at least one of these areas:

- Enzyme design or redesign.
- Enzyme function prediction.
- Substrate specificity.
- Catalytic site discovery or engineering.
- Enzyme stability, expression, or activity optimization.
- Directed evolution with computational or AI support.
- Computational biocatalysis.
- Enzyme datasets, benchmarks, or reusable tools.
- Important reviews or perspectives for enzyme AI.

## Priority

High-priority papers usually have one or more of these properties:

- Clear enzyme-specific contribution.
- Experimental validation.
- Reusable model, dataset, benchmark, or code.
- Strong application relevance.
- Methodological insight for enzyme design or engineering.

## Exclusion Rules

Do not accept papers that are only weakly related, such as:

- General protein design papers with no enzyme-specific relevance.
- Generic docking or molecular modeling papers without enzyme application.
- News, blog posts, or press releases without a primary paper.
- Papers where "enzyme" appears only as a minor keyword.
- Duplicates of existing preprint or published records.

## Preprint and Published Versions

If a preprint later becomes a published paper, keep a single paper record and
add both preprint and published links when possible. Do not add a duplicate
paper record unless the published version is substantially different and should
be curated separately.

## Curator Notes

Curator-written notes should be short and original. They should explain:

- What the paper contributes.
- Why it matters for enzyme AI or computational enzyme work.
- Any important limitation if it affects interpretation.

Do not copy the paper abstract.

## Label Workflow

Maintainers use GitHub labels as the normal review interface:

- `accepted`: include the paper in the archive.
- `needs-info`: ask the submitter for more context.
- `rejected`: decline the suggestion.

The weekly digest is generated from accepted paper records. Do not ask
contributors to provide week IDs or canonical YAML metadata.

## Public URL Boundary

The curation automation only accepts public `http` or `https` URLs. Localhost,
private IP ranges, `.local` hosts, and non-standard ports are rejected before
metadata lookup or accepted-record generation. This keeps the public suggestion
queue from becoming a proxy for internal or local network access.
