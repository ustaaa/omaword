#!/usr/bin/env bash
# User-local Linux pilot; never changes MIME defaults or the WordCraft installation.
# Install:   packaging/linux/install-pilot.sh /absolute/path/package.tar.gz pilot-20261029
# Inspect:   packaging/linux/install-pilot.sh /absolute/path/package.tar.gz pilot-20261029 --dry-run
# Uninstall: packaging/linux/install-pilot.sh --uninstall
# Uninstall removes only this installer's symlinks. Version folders remain for recovery;
# inspect ~/.local/share/omaword/versions and remove individual retired folders yourself.
set -euo pipefail
python3 - "$@" <<'PY'
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import struct
import sys
import tarfile
import tempfile
import uuid

APP = 'io.github.ustaaa.OmaWord'
p = argparse.ArgumentParser(description='Install a reviewed OmaWord native tarball for this user only.')
p.add_argument('archive', nargs='?')
p.add_argument('id', nargs='?', help='unique version label; letters, digits, dots, underscores and hyphens')
p.add_argument('--dry-run', action='store_true')
p.add_argument('--uninstall', action='store_true')
a = p.parse_args()
home = Path.home()
base = home / '.local/share/omaword'
versions = base / 'versions'
current = base / 'current'
marker = '.omaword-pilot.json'


def fail(message):
    raise ValueError(message)


def directory(path):
    """Refuse links/non-directories anywhere below HOME, including shared parent folders."""
    relative = path.relative_to(home)
    cursor = home
    for part in relative.parts:
        cursor /= part
        if cursor.is_symlink() or (cursor.exists() and not cursor.is_dir()):
            fail(f'Expected a real directory, refusing {cursor}')


def managed_current():
    if not current.is_symlink():
        if current.exists():
            fail(f'Refusing existing non-symlink {current}')
        return
    target = Path(os.readlink(current))
    if not target.is_absolute():
        target = current.parent / target
    if target.parent != versions or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', target.name):
        fail(f'Refusing unrelated current symlink: {current}')
    directory(target)
    info = target / marker
    if info.is_symlink() or not info.is_file() or json.loads(info.read_text()).get('installer') != 'omaword-pilot/1':
        fail(f'Existing current target is not a recognized pilot: {target}')


def links():
    pairs = [(home / '.local/bin' / name, current / 'bin' / name) for name in ('omaword', 'omaword-cli')]
    pairs.append((home / '.local/share/applications' / f'{APP}.desktop', current / 'share/applications' / f'{APP}.desktop'))
    for size in ('16x16', '24x24', '32x32', '48x48', '64x64', '128x128', '256x256', '512x512', 'scalable'):
        extension = 'svg' if size == 'scalable' else 'png'
        relative = Path('share/icons/hicolor') / size / 'apps' / f'{APP}.{extension}'
        pairs.append((home / '.local' / relative, current / relative))
    return pairs


def check_links(pairs):
    for destination, target in pairs:
        directory(destination.parent)
        if destination.is_symlink():
            if os.readlink(destination) != str(target):
                fail(f'Refusing unrelated symlink: {destination}')
        elif destination.exists():
            fail(f'Refusing existing file: {destination}')


def main():
    directory(versions)
    managed_current()
    pairs = links()
    check_links(pairs)
    if a.uninstall:
        if a.archive or a.id:
            fail('--uninstall takes no archive or id')
        for destination, _ in pairs:
            if destination.is_symlink():
                if not a.dry_run:
                    destination.unlink()
                print(f'Remove link: {destination}')
        if current.is_symlink():
            if not a.dry_run:
                current.unlink()
            print(f'Remove link: {current}')
        print(f'Version files retained at {versions}. MIME defaults were not changed.')
        return
    if not a.archive or not a.id or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', a.id):
        fail('Provide an archive and a unique safe version id (1–80 characters).')
    destination = versions / a.id
    if destination.exists() or destination.is_symlink():
        fail(f'Version already exists; choose a new id: {destination}')
    if not a.dry_run and platform.system() != 'Linux':
        fail('Installation is supported on Linux only; --dry-run can inspect elsewhere.')
    with tarfile.open(a.archive, 'r:gz') as archive:
        members = archive.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 3 * 1024**3:
            fail('Archive exceeds pilot limits (10000 entries, 3 GiB unpacked).')
        records = {}
        roots = set()
        for item in members:
            path = PurePosixPath(item.name)
            if path.is_absolute() or '..' in path.parts or '\\' in item.name or not path.parts:
                fail(f'Unsafe archive path: {item.name!r}')
            if not (item.isdir() or item.isfile()) or item.mode & 0o7000:
                fail(f'Unsupported archive entry or special permissions: {item.name!r}')
            roots.add(path.parts[0])
            relative = PurePosixPath(*path.parts[1:])
            if relative in records:
                fail(f'Duplicate archive path: {item.name!r}')
            records[relative] = item
        if len(roots) != 1 or not next(iter(roots)).startswith('omaword-'):
            fail('Expected exactly one omaword-* FHS archive root.')
        # No link following, implicit overwrite, devices or archive-controlled ownership.
        for path in records:
            for parent in path.parents:
                if parent in records and not records[parent].isdir():
                    fail(f'File used as an archive directory: {parent}')
        for name in ('omaword', 'omaword-cli'):
            entry = records.get(PurePosixPath('bin', name))
            if entry is None or not entry.isfile() or not entry.mode & 0o111:
                fail(f'Missing executable bin/{name}')
            with archive.extractfile(entry) as stream:
                header = stream.read(20)
            if len(header) < 20 or header[:5] != b'\x7fELF\x02' or header[5] != 1:
                fail(f'Expected a 64-bit little-endian Linux ELF executable: {name}')
            expected = {'x86_64': 62, 'aarch64': 183, 'arm64': 183}.get(platform.machine())
            if expected is None or struct.unpack('<H', header[18:20])[0] != expected:
                fail(f'Archive CPU architecture does not match this machine: {name}')
        for _, target in pairs[2:]:
            relative = PurePosixPath(target.relative_to(current).as_posix())
            if relative not in records or not records[relative].isfile():
                fail(f'Missing desktop/icon asset: {relative}')
        if PurePosixPath(marker) in records:
            fail('Archive contains reserved installer metadata.')
        print(f'Validated {a.archive}; install as {destination}')
        if a.dry_run:
            print('Dry run: no files changed.')
            return
        versions.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.install-', dir=versions))
        try:
            for relative, item in records.items():
                path = staging.joinpath(*relative.parts)
                if item.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(item) as source, path.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    path.chmod(0o755 if item.mode & 0o111 else 0o644)
            # Desktop Exec has its own escaping rules; quote the absolute path and neutralize % codes.
            executable = str(current / 'bin/omaword')
            if '\n' in executable or '\r' in executable:
                fail('Unsupported newline in home directory.')
            escaped = executable.replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$').replace('%', '%%')
            desktop = staging / 'share/applications' / f'{APP}.desktop'
            text = desktop.read_text()
            if len(re.findall(r'^Exec=.*$', text, re.M)) != 1 or len(re.findall(r'^TryExec=.*$', text, re.M)) != 1:
                fail('Expected exactly one Exec and TryExec in the desktop entry.')
            text = re.sub(r'^Exec=.*$', lambda _: f'Exec=env OMAWORD_WAYLAND=1 "{escaped}" %F', text, flags=re.M)
            text = re.sub(r'^TryExec=.*$', lambda _: 'TryExec=' + executable.replace('\\', '\\\\').replace('\t', '\\t'), text, flags=re.M)
            desktop.write_text(text)
            (staging / marker).write_text(json.dumps({'installer': 'omaword-pilot/1', 'id': a.id, 'appId': APP}) + '\n')
            staging.rename(destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)  # Only our newly created random staging folder.
        for link, target in pairs:
            link.parent.mkdir(parents=True, exist_ok=True)
            if not link.is_symlink():
                link.symlink_to(target)
        temporary = base / f'.current-{uuid.uuid4().hex}'
        temporary.symlink_to(Path('versions') / a.id)
        os.replace(temporary, current)
        print(f'Installed OmaWord pilot {a.id}. Launch: {home / ".local/bin/omaword"}')
        print('WordCraft and MIME defaults are unchanged. To remove launcher links, run this script --uninstall.')

try:
    main()
except (OSError, ValueError, tarfile.TarError) as error:
    print(f'Pilot installation refused/failed: {error}', file=sys.stderr)
    sys.exit(1)
PY
