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
