# Hermes Coach

## Source Of Truth

- Treat the deterministic engine as the source of truth for training decisions.
- Read `docs/EMBASAMENTO-CIENTIFICO.md` for the algorithmic contract. It is the
  single source for both the algorithmic contract and the zone table
  (`ZONE_BANDS`, mirrored from `src/coach.py`); the vault copy is a mirror like
  every other document.
- Distinguish in prose and code: **scientific evidence**, **system heuristic**, and
  **computational model**. A heuristic or model must not be presented as physiology.
- FTP is an operational power reference; do not equate it automatically with MLSS,
  LT, RCP, or Critical Power.
- References must be verifiable. Never invent an author, DOI, PMID, result, or claim.
- Many documents exist in **both** the repo and the Obsidian vault
  (`~/Documents/Obsidian Vault/DevOps/01-Projetos/cycling-coach/`). Default owner is
  the **repo**; the vault copy is a mirror for reading. Edit the repo, then
  synchronize with the official utility — `python3 scripts/sync_vault_docs.py
  --check`, then `--sync-all` or `--sync DOC`. **Never copy-paste a mirror by
  hand**: doing so duplicated four mirror bodies and destroyed four ownership
  blocks (PROMPT 30).
  Each mirrored file states its owner at the top. Verify ownership before editing
  either copy. There is no exception to this rule. The tool, the mapping and its
  guarantees live in `docs/VAULT-SYNC.md`.
- `docs/EMBASAMENTO-CIENTIFICO.md` used to be exempted, on the claim that a
  scientific Z1-Z7 table was canonical in the vault because `ZoneIntegrityTest`
  compared both sides. That claim was wrong on both counts and is not to be
  reintroduced: `ZoneIntegrityTest` (`tests/test_plan.py`) compares
  `src/coach.py:ZONE_BANDS` against a literal inside the test and reads no
  markdown, and no Z1-Z7 table with %FCmax / threshold / RPE columns exists in
  either location. If such a table is ever written, its authority has to be
  established from real evidence — not inferred from a mirror rule.

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
