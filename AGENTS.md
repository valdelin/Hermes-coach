# Hermes Coach

## Source Of Truth

- Treat the deterministic engine as the source of truth for training decisions.
- Read `docs/EMBASAMENTO-CIENTIFICO.md` for the algorithmic contract. The complete
  scientific Z1-Z7 table is canonical in the Obsidian vault path named by that file.
- Distinguish in prose and code: **scientific evidence**, **system heuristic**, and
  **computational model**. A heuristic or model must not be presented as physiology.
- FTP is an operational power reference; do not equate it automatically with MLSS,
  LT, RCP, or Critical Power.
- References must be verifiable. Never invent an author, DOI, PMID, result, or claim.
- Many documents exist in **both** the repo and the Obsidian vault
  (`~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/`). Default owner is
  the **repo**; the vault copy is a mirror for reading. Edit the repo, then copy.
  Each mirrored file states its owner at the top. The one deliberate exception is
  the scientific Z1-Z7 table, which lives in the vault because `ZoneIntegrityTest`
  compares both sides. Verify ownership before editing either copy.

## Engineering Loop

- Before editing, inspect the related modules and run `git status`.
- Preserve persisted formats and external contracts unless a migration is explicit:
  `plan.json`, focus string values, and Intervals.icu event identifiers are examples.
- Keep changes within the requested scope. Explain any required adjacent change.
- Follow the project's existing type-hint conventions in Python changes.
- Add or update focused tests; do not remove tests to make the suite pass.
- Run focused tests during implementation and the CI-equivalent suite before finishing:
  `python3 -m unittest discover -s tests -v`.
- Run `git diff --check`, inspect `git status`, and summarize the diff before proposing
  a commit. Never commit, tag, push, publish, or modify the Intervals calendar without
  explicit user approval.

## Domain Guardrails

- `ZONE_BANDS` is a verified invariant. Preserve declared-zone intensity when fitting
  budget; reduce volume before lowering power and never lower below the zone floor.
- Treat active recovery as session intent within Z2, not as a standalone Z1 focus.
- Treat a missed active-recovery session as non-absorbable. Do not replace missed
  Limiar/VO2 work with base volume.
- Update the scientific documentation when a change modifies a physiological rule,
  zone definition, or training-load policy.
