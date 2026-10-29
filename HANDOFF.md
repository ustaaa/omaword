# OmaWord handoff — 2026-10-29

## Verified implementation

- Fork created at `ustaaa/omaword`, local branch `codex/omarchy-ui`, exact upstream WordCraft v0.12.0 `3de6ff95af86c19d67030cd96dba15cd6a45a25e`.
- Omarchy v3/v4 bounded background palette/font discovery; last-good recovery. Manual themes stay fixed. Original document/font database/layout/render/file-format crates unchanged.
- Chrome uses dedicated font aliases; original families, page rendering, IME composition, comments and annotations preserve upstream fonts. Font activation occurs only during an idle real UI pass, so hidden logic cannot arm an input-losing future gate.
- OmaWord binary/desktop/icon/profile/recovery/control namespace; no upstream updater. MCP protocol name and all 648 command records remain upstream-compatible.
- Binary retains upstream X11 fallback when DISPLAY exists; installed native pilot desktop explicitly sets `OMAWORD_WAYLAND=1` for compositor scaling. Explicit `OMAWORD_X11=1` overrides it.

## Verification and installed state

- Halo full `cargo xtask ci`: all 8 gates PASS (fmt, clippy, workspace tests, i18n-report, doctest, assets, layers, wasm). UI units: 994 passed, 2 inherited ignored. Real text/hidden-logic/next-frame font regression and rendered document appearance parity PASS. Evidence: `dist/validation/ci-amd64.log`.
- Independent native/DOCX synthetic corpus: 2/2 PASS; style, table, edit/undo/redo/save/reopen and rendered page pixels match exact upstream. All 648 command records identical. `dist/validation/corpus-amd64-r1/`.
- Final ARM64 release and native Wayland smoke PASS; app ID and dynamic title verified. Authentication refusal and key mode 0600 verified. Document inspect and page PNG hash unchanged through manual/system/missing/invalid/live/restored theme states. Real desktop theme and clipboard untouched. Evidence/screenshots: `dist/validation/native-arm64/`.
- Installed on OmarchyMax under `/home/irtek/.local/share/omaword/versions/pilot-20261029`, launchers in `~/.local/bin` and `~/.local/share/applications`. Normal `gtk-launch io.github.ustaaa.OmaWord` verified PID 454515, class `io.github.ustaaa.OmaWord`, title `OmaWord`, `xwayland=false`, 786×647 logical at the user's 1.6 scale. No control listener is left open. Installed binary equals final build SHA-256 `0601c6d7065401af9178ec8f30044ed0ff41ddb2215bdf6789b988fcd4fd8db0`.
- ARM package copied locally: `dist/release/omaword-0.12.0-linux-aarch64.tar.gz`. Installer preserves unrelated files, version history and MIME defaults.

## Mechanical work handed to root after the user's model-cost correction

No further expensive coding/review expansion. The final x86_64 release/package job completed on Halo. Its logs are preserved at `dist/validation/omaword-amd-final.log` and `dist/validation/omaword-amd-package.log`; the release log ends with a successful optimized build, and the package log records the tarball path. The copied artifact is `dist/release/omaword-0.12.0-linux-x86_64.tar.gz`; its SHA-256 (`9453263c197f7f0d92ac4904940044259408e2bcce848cbccfde07cd8b464a03`) matches the source artifact on Halo. Initial x86 release gates had already passed; the final run includes the backend/launcher correction.

Source changes are committed and pushed on `codex/omarchy-ui`; no PR is required. OmarchyMax and Halo prototype checkouts are both clean at commit `6173f3f6` and track `origin/codex/omarchy-ui`. Their previous prototype changes are preserved in named stashes: `codex/omaword prototype backup OmarchyMax 2026-10-29` and `codex/omaword prototype backup Halo 2026-10-29`. On both hosts, `origin` is the OmaWord fork and `upstream` is `https://github.com/storytold/wordcraft.git`; Halo additionally retains its local baseline clone as `baseline-source`. Preserve ignored `dist/` evidence. Owner explicitly authorized direct commits/pushes without Nomura prerequisite; scoped AGENTS.md records this.

## Remaining acceptance / limits

Physical IME, clipboard formats, file drag/drop, portal chooser/printing and input-to-photon latency are not claimed tested. Inherited Flatpak/macOS/Windows descriptors remain upstream packaging references; only the new native Linux tar/pilot installer is supported here. New fork-only translation labels fall back to English while all 27 pinned upstream catalogs are embedded. Build inputs are exact pins in UPSTREAM.toml; do not change the shared OmaGrid font checkout.
