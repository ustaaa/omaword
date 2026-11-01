# OmaWord engineering handoff

## Development lifecycle

OmaCraft coordinates exact revisions, independent reviews and cross-platform evidence at
https://github.com/ustaaa/omacraft. This repository keeps its own upstream history.
Use origin for the Oma fork and upstream for the original project. Work on a topic branch,
review the diff, run relevant gates, and open a draft pull request. Do not automatically
publish releases or overwrite another device's dirty checkout.

## Current pilot (2026-10-30)

Linux ARM64 and x86_64 pilot binaries have been built. Native Wayland launch and sample
rendering were checked at display scales 1.6 and 1.5 respectively. This is not full
keyboard, IME, clipboard, accessibility or document-compatibility certification.
The ribbon and command layout are retained. Appearance must not modify document state.
macOS build workflows are experimental and manual; no Oma macOS distribution is certified.

Full Linux quality gates passed during pilot preparation. Fresh synthetic corpus comparisons
passed for Grid (3 cases), Word (2) and Deck (2); Notes CLI smoke passed 20 checks.
A previous x86 Notes UI test process terminated with SIGSEGV at four test threads.
All 121 UI tests then passed serially and under a debugger; full serial CI passed.
The cause remains unresolved. Do not describe reruns as a fix or hide this risk.

## Next review

Review downstream identity, theme isolation, font reload, package/updater separation,
and the declared support matrix. Revalidate at the exact reviewed commit and record
compiler, target, commands, result, skipped checks and logs. Keep private machine paths,
notebooks, credentials and infrastructure inventory out of tracked reports.

### OmaCraft brand polish (2026-10-30)
Suite links and documentation now use ustaaa/omacraft. Original application icon
regenerated in the shared dark-tile/paper style, with a distinct application accent.
PNG/SVG/ICO structure (where applicable), deterministic regeneration and whitespace
checks passed. No engine, document, command, dependency or version changes.
Installed-app validation of these new assets is still pending; previous runtime
evidence does not cover this polish. Existing CI limitations remain open.

### Suite review follow-up (2026-10-31)
Linux pilot policy now documents native Wayland and `OMAWORD_X11=1`; legacy
`WORDCRAFT_WAYLAND` remains accepted. The upstream WordCraft Linux packager and
Flatpak bundler fail clearly as disabled; the active OmaWord package derives its
version from Cargo metadata. The `OmaWord User` author default remains, documented as
format-visible. Shell syntax and diff whitespace checks pass; Rust build/runtime not run.

### Candidate 2 review fixes (2026-10-31)
Theme selection now promotes a valid preferred root after legacy removal, preserves the
last good snapshot during invalid updates, and checks/deduplicates HOME/.local/state
beside custom XDG_STATE_HOME. X11 override accepts only `=1`. Focused Cargo tests were
blocked before compile by the unwritable shared Cargo git database; rustfmt passed.

### Upstream variable isolation by Claude (2026-10-31; branch claude/identity-env)
Running without preferences is now `OMAWORD_NO_PREFS`; `WORDCRAFT_NO_PREFS` is no longer
read, so an upstream WordCraft test setting cannot switch off OmaWord preferences or
recovery. The control port was already `OMAWORD_CONTROL_PORT` only; its help text and
the three app integration tests still set the upstream names and so no longer tested
anything, and now use the OmaWord names. Behaviour switches (`WORDCRAFT_REGION`,
`_LANGUAGE`, `_DICTIONARIES`, `_SPEECH`, `_FILE_DIALOG`, `_PASSWORD`, `_CARET_GLIDE_MS`)
and `WORDCRAFT_WAYLAND` keep their upstream names. The fonts crate change is a comment.

### Alpha version reporting (2026-11-01)
Downstream label `0.12.0-oma.1.alpha.1` is shown by GUI About and
`omaword --version` / `omaword-cli --version`; output names upstream WordCraft 0.12.0
separately. The Linux pilot package uses the downstream label and includes `VERSION.txt`
with both versions. Cargo package versions and lockfile are unchanged. Rust builds/runtime
and package artifact verification are delegated to Halo; local formatting, shell syntax
and diff whitespace checks passed.

### WordCraft 0.13.2 integration candidate (2026-11-01)
Isolated integration branch `codex/upstream-word-0.13.2` starts at OmaWord alpha 1
`cefcb752f17cd3c62d1a2c5ea2046390164361df` and merges upstream tag `v0.13.2`,
resolved to `2be33e6dc9c246a57995b131ee85491ce81de328`. Kept workspace/Cargo package
version at upstream `0.13.2`; `OMA_VERSION` is `0.13.2-oma.1.alpha.1` so the UI and
CLI continue to report both identities correctly.

Resolved four true merge conflicts: AGENTS.md combines OmaWord lifecycle/delegation
instructions with upstream CI guidance; Cargo.lock takes upstream's refreshed lock,
then retains the fork's `craft-platform` appearance dependency (including its lock
entry) and exact app version split; `apps/wordcraft/src/main.rs` keeps OmaWord X11,
identity and preference handling and omits upstream's Windows self-update finalizer;
`crates/ui-egui/src/updates_ui.rs` keeps the installation-managed update notice and
removes upstream network updater behavior. This retains Omarchy palette/fonts and
ribbon patches while accepting upstream command, document, table, printing and
localization work.

Upstream workspace diff adds `wordcraft-metafile` to formats and includes upstream's
`craft-update` revision change (`92d392c…` to `04aa170…`); the former is required by
new format code, and the latter remains compiled but is not invoked by OmaWord's
installation-managed update UI. No downstream font or catalog revision was changed;
`craft-i18n.rev` remains `9205108cfdced5177706264038848b68b2422d2b`. At this preparation
host, rustc/cargo are 1.99.1; `CRAFT_FONTS_DIR`, `CRAFT_I18N_DIR`, and
`CARGO_TARGET_DIR` are unset. Thus this host supplied no external font/catalog inputs;
font and localization build evidence is delegated to the designated Halo validation.
Local checks: `cargo fmt --all -- --check` passed; `git diff --check` passed. No compile,
tests, font build or i18n embedding was run here. This is an integration candidate only;
not pushed, merged to pilot/main, tagged, or deployed.
