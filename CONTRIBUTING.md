# Contributing to FAIRy-core

🎋 Thanks for your interest in FAIRy-core!

FAIRy-core is the local-first validation engine for FAIR research data.
It powers rulepack-based checks and reports for datasets across domains
(omics, museums, etc.).

We welcome contributions from data stewards, curators, researchers, and
developers—especially around rule types, rulepacks, tests, and documentation.

> Before contributing, please read our [Code of Conduct](./CODE_OF_CONDUCT.md).

---

## Ways to contribute

There are many useful ways to help:

- **Use FAIRy-core** and open issues for bugs, confusing behavior, or rough edges.
- **Improve the engine**: rule types, report schema stability, performance.
- **Add or refine rulepacks** (especially for real repositories like ENA, GEO,
  museum standards, etc.).
- **Improve tests and fixtures**, including golden tests.
- **Improve documentation**: README, PRDs/specs, examples.

If you’re new, look for issues labeled `good first issue` or `help wanted`
in the issue tracker.

---

## Getting started

1. **Find or open an issue**

   - Check the [issue tracker](../../issues) for something interesting.
   - New contributors: start with `good first issue` or `help wanted`.
   - For new ideas, open an issue to discuss before you start coding.

2. **Fork and clone the repository**

   - Fork this repo on GitHub.
   - Clone your fork locally:

     ```bash
     git clone https://github.com/<your-username>/fairy-core.git
     cd fairy-core
     ```

3. **Create a feature branch**

   ```bash
   git switch -c feat/short-description

4. **Set up your environment**

    - Create and activate a virtual environment
    - Install dependencies (including dev tools) according to the README:

   ```bash
   pip install -e ".[dev]"
    ```
    - Install pre-commit hooks if configured:
    ```bash
    pre-commit install
    ```
5. **Make your changes**

   - Keep changes focused and small where possible
   - Update or add tests as needed.
   - Update documentation if behavior or APIs change
6. **Run checks locally**

   - Run the test suite (e.g. pytest).
   - Run linters/formatters (e.g. pre-commit run --all-files).

7. **Submit a Pull Request**

   - Push your branc to your fork:
    ```bash
    git push -u origin feat/short-description
    ```
   - Open a Pull Request (PR) against the main branch of yuummmer/fairy-core.
   - In the PR description, include:
        - a short summary of what you changed and why
        - a reference to the issue number (e.g. Fixes #42)
        - any notes for reviewers (breaking changes, migration notes, etc.)

We will review your PR as soon as we can. Friendly pings on status are welcome.
---

## Specs & PRDs

Product Requirements Documents (PRDs) and design specs are maintained in docs/prd/:

- Preflight Report Schema v.1.0.0
    Stable JSON schema for fairy preflight reports.

These documents serve as living "contract" documentation for downstream users
and help contributors understand design decisions. If you are working on
something that touches these areas, please skim the relevant PRD first and
reference it in your PR.

---

## Maintainers & module stewards

At the moment, FAIRy-core is primarily maintained by the project founder.

We're interested in building a small group of module stewards
(maintainers-in-training) who can help own specific areas, such as:

- Rule types and engine internals
- Rulepacks and repository-aligned checks (ENA, GEO, museum data, etc.)
- Tests and golden fixtures
- Documentation and examples

If you’re interested in a longer-term role, see MAINTAINERS.md and the
pinned issue in the tracker (e.g. “Call for module stewards / maintainers”)
for details on how to get involved.

---
## Licensing of contributions

By contributing to this repository, you agree that:

- Contributions to the core engine code (e.g. files under src/fairy/**
excluding src/fairy/rulepacks/**) are licensed under the project’s main
license, AGPL-3.0-only.
- Contributions to built-in rulepacks (e.g. files under
src/fairy/rulepacks/**) are licensed under CC0-1.0, so they can be
freely reused by the wider community.
- Contributions to samples and test fixtures (e.g. under samples/**
or tests/fixtures/**, if present) are licensed under CC BY-4.0.

f you are contributing code or content copied or adapted from another project,
please make sure its license is compatible with the relevant FAIRy license and
include attribution where needed.

Note: We may introduce a Contributor License Agreement (CLA) later to make
dual/commercial licensing simpler. If that happens, this document will be
updated, and new contributions may be subject to CLA terms going forward.
---
