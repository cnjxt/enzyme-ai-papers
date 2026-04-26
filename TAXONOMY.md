# Taxonomy

Canonical tags are defined in `data/taxonomy.yml`. Use only canonical tag IDs in
paper YAML files.

## Topics

Topics describe the scientific task or paper type.

Examples:

- `enzyme-design`
- `function-prediction`
- `substrate-specificity`
- `biocatalysis`
- `benchmark-dataset`

## Methods

Methods describe the main computational approach.

Examples:

- `protein-language-model`
- `diffusion-generative-model`
- `structure-based-design`
- `active-learning`
- `molecular-dynamics`

## Evidence

Evidence describes the validation level.

Examples:

- `computational-only`
- `benchmark-only`
- `retrospective-validation`
- `wet-lab-validation`
- `industrial-application`

## Applications

Applications describe the domain where the enzyme work is used or motivated.

Examples:

- `pharma-synthesis`
- `plastic-degradation`
- `metabolic-engineering`
- `environment`
- `general`

## Adding Tags

Add new tags conservatively. A new tag should be added only if:

- Several papers need it.
- It is distinct from existing tags.
- It improves browsing and filtering.

When in doubt, use an existing broader tag.
