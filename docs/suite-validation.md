# OmaWord validation against upstream

Baseline: `wordcraft` v0.12.0, `3de6ff95af86c19d67030cd96dba15cd6a45a25e`. The manifest pins this source identity; binary provenance must be supplied by the build log (a version string alone cannot attest a commit). No engine, document model, import/export or render changes are part of this adaptation.

## Executable corpus

Run upstream and fork on the **same host**, with the same `CRAFT_FONTS_DIR` at build time and the same installed fonts at runtime. Do not rebuild or replace either binary during a run. Python 3.9+ standard library only:

```sh
python3 -m unittest discover -s tools/omarchy-validation -p 'test_*.py'
python3 tools/omarchy-validation/corpus.py \
  --upstream /absolute/path/wordcraft-cli \
  --fork /absolute/path/omaword-cli \
  --output dist/validation/corpus-new-run
```

The output directory must not exist. Every command, stdout, stderr, source fixture, edited output, observation and rendered PNG is retained there. All fixtures are contributor-original synthetic text/geometry generated through upstream's command API; no office application or real user document is involved. Generated binaries/documents stay under ignored `dist/`, never in Git.

Each of two cases (native format and OOXML) creates a formatted document/presentation with a table, saves it, opens the **same input** in upstream and fork, edits, verifies undo removes the edit and redo restores it, saves another file, and reopens in a fresh CLI process. Input is made read-only and its hash is checked after each implementation; binary hashes are recorded and checked again at the end. The runner compares full command results, inspected content/style data and exact PNG hashes for every page/slide. Word renders use en-US region and UTC. Only per-save Word created/modified timestamps and evidence-directory prefixes in top-level file paths are normalized. Raw results remain available.

Failures are nonzero exit, malformed/missing responses, warning text on stderr, nonempty explicit warning/loss fields, expected content missing, changed undo/redo results, lost tables, different styles/semantics, different rendered pixels, input mutation or binary replacement. Deck open responses must expose `lostSlides`, `damagedMedia`, and `missingFonts`; loss/damage must be empty. Missing fonts are retained and compared, not suppressed or claimed installed. The Word file API does **not** expose a general data-loss/no-oracle field: absence is not an interoperability oracle. Any future explicit `no_oracle`/warning field is checked, never discarded.

## Scope and acceptance gates

- Corpus pass proves no observed fork regression in these two small generated cases on the named host. It does not prove Microsoft Office equivalence, complex external document fidelity, broad OOXML coverage or native UI correctness.
- Preserve UI/document font role tests: theme changes must leave document font chains, content colours and render engine untouched; IME/text events must survive a pending font refresh.
- Run the repo's required Rust CI (including formatting, clippy, tests, layers, asset checks, WASM where supported); record any skipped target explicitly.
- On actual Omarchy: inspect light/dark palette transitions, manual appearance mode, invalid/missing theme fallback, font changes while typing, notes/comments, save/reopen, file picker and clipboard. CLI PNG parity cannot validate egui notes/comments or physical keyboard behavior.
- Check desktop ID, icon, MIME association, isolated config/control token namespace, CLI help/version, window title, and disabled upstream updater. Native tar is the first runtime acceptance target; Flatpak theme-file access remains a separate sandbox gate.
- Rehearse upstream integration against a genuinely divergent upstream revision in an isolated checkout before merging, then rerun these gates. The manifest baseline changes only with an intentional upgrade.

## Recorded results

Harness fault-injection tests and real corpus outcomes are recorded below as execution occurs. A checked-in script is not a completed runtime gate.

- 2026-10-29, UrazHalo amd64: **2/2 corpus cases passed** (`dist/validation/corpus-amd64-r1/report.json`). Upstream pinned v0.12.0 release CLI versus fork release CLI: native `.wcraft.json` and `.docx` content/styles/table observations, edit/undo/redo/save responses and every page PNG hash matched. No stderr or explicit structured warnings occurred; Word exposes no general loss warning oracle. Input and binary hashes remained unchanged. The complete JSON command catalog also matched (`catalog.json`).
- Validator fault injection: 6 tests passed locally. UI input/palette tests are separate gates; see the build/test handoff for their outcomes.

- Final OmaWord UI validation on UrazHalo passed: `omarchy_parity` integration test preserves full serialized Document, revision/dirty/history state and rendered page pixels across dark/light/removal of the palette. The internal physical Text test also passed with a hidden `run_logic` tick before the next input frame; manual appearance/document-state checks passed. The production owner reports full required CI **8/8 gates passed**, with UI unit results **994 passed, 2 inherited ignored**. This supersedes the earlier pending UI-test status; live installed-session acceptance remains separate.
