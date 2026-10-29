#!/usr/bin/env bash
# Package the already-verified native release binaries, preserving third-party notices.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TARGET=${CARGO_TARGET_DIR:-$ROOT/target}
FONT_DIR=${CRAFT_FONTS_DIR:?Set CRAFT_FONTS_DIR to the pinned font checkout used for the build}
I18N_DIR=${CRAFT_I18N_DIR:?Set CRAFT_I18N_DIR to the pinned translation checkout}
VERSION=0.12.0
ARCH=$(uname -m)
case "$ARCH" in aarch64|x86_64) ;; *) echo "Unsupported architecture: $ARCH" >&2; exit 2;; esac
BASE="omaword-$VERSION-linux-$ARCH"
mkdir -p "$ROOT/dist/release"
STAGE=$(mktemp -d "${TMPDIR:-/tmp}/omaword-package.XXXXXXXX")
trap 'rm -rf "$STAGE"' EXIT
TREE="$STAGE/$BASE"
install -Dm755 "$TARGET/release/omaword" "$TREE/bin/omaword"
install -Dm755 "$TARGET/release/omaword-cli" "$TREE/bin/omaword-cli"
install -Dm644 "$ROOT/packaging/linux/io.github.ustaaa.OmaWord.desktop" "$TREE/share/applications/io.github.ustaaa.OmaWord.desktop"
for size in 16 24 32 48 64 128 256 512; do
  install -Dm644 "$ROOT/assets/omaword-icon/$size/io.github.ustaaa.OmaWord.png" "$TREE/share/icons/hicolor/${size}x${size}/apps/io.github.ustaaa.OmaWord.png"
done
install -Dm644 "$ROOT/assets/omaword-icon/io.github.ustaaa.OmaWord.svg" "$TREE/share/icons/hicolor/scalable/apps/io.github.ustaaa.OmaWord.svg"
DOC="$TREE/share/doc/omaword"
mkdir -p "$DOC/fonts-bundled" "$DOC/craft-fonts"
for file in LICENSE-MIT LICENSE-APACHE ATTRIBUTION.md; do install -m644 "$ROOT/$file" "$DOC/$file"; done
cp -R "$ROOT/assets/fonts/." "$DOC/fonts-bundled/"
# Include the exact pack's licensing tree and manifest; font bytes are already embedded.
find "$FONT_DIR" -type f \( -iname '*license*' -o -iname '*ofl*' -o -name 'manifest.txt' -o -name 'ATTRIBUTION.md' -o -name 'README.md' \) -not -path '*/.git/*' | while IFS= read -r file; do
  rel=${file#"$FONT_DIR/"}; install -Dm644 "$file" "$DOC/craft-fonts/$rel"
done
for file in "$I18N_DIR"/LICENSE*; do
  test -f "$file" && install -Dm644 "$file" "$DOC/craft-i18n/$(basename "$file")"
done
if command -v desktop-file-validate >/dev/null; then desktop-file-validate "$TREE/share/applications/io.github.ustaaa.OmaWord.desktop"; fi
tar -C "$STAGE" -czf "$ROOT/dist/release/$BASE.tar.gz" "$BASE"
sha256sum "$ROOT/dist/release/$BASE.tar.gz" > "$ROOT/dist/release/$BASE.tar.gz.sha256"
printf '%s\n' "$ROOT/dist/release/$BASE.tar.gz"
