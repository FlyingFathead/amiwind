#!/usr/bin/env python3
"""Build, independently validate and promote an immutable source archive."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external
from project_version import public_version, check_native_versions

PROJECT = "amiwind"
EXECUTABLES = {"build.sh", "tools/AmiWind-FS-UAE-launcher.py", "tools/run_fs_uae.py"}
PROJECT_MEDIA = {"resources/media/AmiWind_logo.png", "resources/media/AmiWind_wordmark.png",
                 "resources/media/AmiWind_logo_name_only.png"}
IGNORED_PARTS = {".git", "__pycache__", ".venv", ".pytest_cache"}
DOCUMENTATION_IMAGES = {f"docs/images/amiwind-v0.0.15-dev2-{name}.png" for name in ("dock", "npc", "guard", "town", "waterfront")}
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev2-{name}.png" for name in ("port", "fargoth", "tradehouse", "prison"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev3-{name}.png" for name in ("rock-before", "rock-after", "dialogue"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev4-{name}.png" for name in ("dialogue", "darvame", "tree"))
DOCUMENTATION_IMAGES.add("docs/images/amiwind-v0.0.23-dev5-windows.png")
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc1-{name}.png" for name in ("balmora", "mages"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc2-{name}.png" for name in ("balmora-bridge", "balmora-street", "balmora-river"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.31-balmora-night-{name}.png" for name in ("street-lamp", "plaza-guard", "lamp-house", "river", "house-corner"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc3-{name}.png" for name in ("dagoth", "balmora"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc4-{name}.png" for name in ("map",))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-{name}.png" for name in ("balmora-bridge", "balmora-street", "balmora-river", "dagoth", "map"))
DOCUMENTATION_IMAGES.add("docs/images/amiwind-v0.0.25-dev1-journal.png")
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.25-rc1-{name}.png" for name in ("map", "navigation"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.27-rc2-{name}.png" for name in ("mushroom-cap", "ascadian-mushrooms", "mushroom-underside"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.28-rc1-{name}.png" for name in ("sunrise", "sunset", "night"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.31-toolkit-{name}.png" for name in ("header", "world"))
DOCUMENTATION_CLIPS = {"docs/images/amiwind-v0.0.23-dev2-port.gif"}
TEXT_LIMIT = 262144
# The bug register grows with every bug: its JSON source and the generated table (docs/bugs/README.md).
LARGE_TEXT = {"docs/bugs/bugs.json": 1048576, "docs/BUGS.md": 1048576}
# Whitespace baselines (docs/PATCH-v<version>.json) list every file of the published base release and
# grow with the repository (RELEASE-PATCH-SIZE-33).
LARGE_TEXT_PATTERNS = ((re.compile(r"docs/PATCH-v[0-9][0-9A-Za-z.-]*[.]json"), 1048576),)


def text_limit(name):
    """The release text size limit of one source file (TEXT_LIMIT unless named above)."""
    if name in LARGE_TEXT:
        return LARGE_TEXT[name]
    for pattern, limit in LARGE_TEXT_PATTERNS:
        if pattern.fullmatch(name):
            return limit
    return TEXT_LIMIT
DOCUMENTATION_CLIPS.add("docs/images/amiwind-v0.0.29-rc2-torch.gif")
DOCUMENTATION_IMAGES.update({
    'docs/images/amiwind-v0.0.28-balmora-guard-street.png',
    'docs/images/amiwind-v0.0.28-balmora-moon-rooftops.png',
    'docs/images/amiwind-v0.0.28-balmora-moons.png',
    'docs/images/amiwind-v0.0.28-balmora-street-sky.png',
    'docs/images/amiwind-v0.0.28-night-masser.png',
    'docs/images/amiwind-v0.0.28-night-secunda.png',
    'docs/images/amiwind-v0.0.28-night-stars.png',
    'docs/images/amiwind-v0.0.28-night-wide.png',
    'docs/images/amiwind-v0.0.28-v3-blue-hour.png',
    'docs/images/amiwind-v0.0.28-v3-dawn.png',
    'docs/images/amiwind-v0.0.28-v3-dusk.png',
    'docs/images/amiwind-v0.0.28-v3-golden-hour.png',
    'docs/images/amiwind-v0.0.28-v3-midday.png',
    'docs/images/amiwind-v0.0.28-v3-night.png',
    'docs/images/amiwind-v0.0.28-v3-red-sunset.png',
    'docs/images/amiwind-v0.0.28-v3-sunrise.png',
})
DOCUMENTATION_CLIPS.update({
    'docs/images/amiwind-v0.0.28-day-gallery.gif',
    'docs/images/amiwind-v0.0.28-night-gallery.gif',
})
DOCUMENTATION_IMAGES.update({'docs/images/amiwind-v0.0.29-rc1-torch-night.png', 'docs/images/amiwind-v0.0.29-rc1-high-elf-appearance.png', 'docs/images/amiwind-v0.0.29-rc1-mushroom-prompt.png', 'docs/images/amiwind-v0.0.29-rc1-mushroom-pickup.png', 'docs/images/amiwind-v0.0.29-rc1-audio.png'})
DOCUMENTATION_CLIPS.update({'docs/images/amiwind-v0.0.29-rc1-mushroom-pick.gif'})
DOCUMENTATION_CLIPS.update({'docs/images/amiwind-v0.0.32-gallery.gif'})
DOCUMENTATION_IMAGES.update({'docs/images/amiwind-v0.0.30-temple-before.png', 'docs/images/amiwind-v0.0.30-temple-after.png', 'docs/images/amiwind-v0.0.30-temple-banner.png', 'docs/images/amiwind-v0.0.30-controls.png'})
DOCUMENTATION_IMAGES.update({'docs/images/amiwind-v0.0.32-vivec-bridge-pillar.png', 'docs/images/amiwind-v0.0.32-vivec-canal-night.png', 'docs/images/amiwind-v0.0.32-vivec-sunrise.png', 'docs/images/amiwind-v0.0.32-vivec-red-sky.png', 'docs/images/amiwind-v0.0.32-vivec-bridge-dusk.png', 'docs/images/amiwind-v0.0.32-vivec-bridge-night.png', 'docs/images/amiwind-v0.0.32-vivec-arena-sun.png', 'docs/images/amiwind-v0.0.32-vivec-arena-night.png', 'docs/images/amiwind-v0.0.32-vivec-guard-sun.png', 'docs/images/amiwind-v0.0.32-vivec-sun-between-cantons.png'})
# CHIM-TEXTURE-SPECKS-33: before/after frames and the autumn_glitter_leaves effect (docs/bugs page).
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.33-chim-specks-{name}.png" for name in ("before", "after", "autumn-glitter-leaves"))
# v0.0.33 release notes: graphs drawn by tools/release_graphs.py from docs/performance/CHIM-v0.0.33-MEASUREMENTS.json.
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.33-chim-{name}.png" for name in ("disk", "island", "loading", "frame-jit", "frame-slow", "counters", "memory", "build", "chunkload"))
# v0.0.33 release notes, "Let's fix those bugs": before/after frames (FS-UAE, headlamp off) and one OpenMW reference.
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.33-fix-{name}.png" for name in ("strider-before", "strider-after", "ship-light-before", "ship-light-after", "ship-light-openmw"))
# Project-authored text graphic; retain bounded UTF-8 source validation.
DOCUMENTATION_SOURCE_GRAPHICS = {"docs/images/amiwind-shared-sky-build-comparison.svg"}
# Performance charts written by tools/perf_charts.py from measured numbers.
DOCUMENTATION_SOURCE_GRAPHICS.update(f"docs/images/amiwind-perf-{name}.svg" for name in ("visibility-by-map", "faces-world-vs-funcwall", "seyda-crossing-load"))
# Project-authored bounded command metadata, required by the runtime dispatcher.
DEBUG_CATALOGUES = {"config/debug-commands.txt", "config/shroompicker.txt"}
# Plain-text world tables shipped to id1/world/ (owner-editable, no game data).
WORLD_TABLES = {"config/fog-locations.txt"}
# Project-authored CHIM texture effect definitions: plain-text .chimfx files of the public effects library
# (docs/chim/TEXTURE_EFFECTS.md); no game data.
CHIM_EFFECTS_DIR = PurePosixPath("tools/chim/effects")
# Exact project-authored C include, validated as bounded UTF-8 source.
NATIVE_SOURCE_INCLUDES = {"engine/aga/src/model_alias_stream.inc"}


def allowed_files(root):
    paths = json.loads((root / "tools/release-files.json").read_text(encoding="utf-8"))
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("Invalid source file list")
    if len(paths) != len(set(paths)):
        raise ValueError("Duplicate source file list entry")
    for name in paths:
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or str(p) != name or "\\" in name:
            raise ValueError("Unsafe source file list entry")
        preset = (p.suffix in (".uae", ".fs-uae") and p.parent == PurePosixPath("resources/emulators")) or name in ("config/keymaps.cfg", "config/game.cfg") or name in DOCUMENTATION_IMAGES or name in DOCUMENTATION_CLIPS or name in PROJECT_MEDIA or name in DOCUMENTATION_SOURCE_GRAPHICS or name in DEBUG_CATALOGUES or name in WORLD_TABLES or (p.suffix == ".chimfx" and p.parent == CHIM_EFFECTS_DIR)
        native_aux = name in ("tools/polycount_inspector.html", "amiwind-toolkit/map-inspector.html", "amiwind-toolkit/world-map.html", "amiwind-toolkit/index.html", "amiwind-toolkit/chim-head.js", "tests/test_polycount_markup.js", "tests/test_world_metrics_layer.js", "engine/aga/Makefile", "engine/aga/qc/progs.src", "engine/aga/src/progdefs.q1", "engine/aga/src/progdefs.q2", "docs/aga/COPYING.NEWLIB", ".github/workflows/source-check.yml")
        if not preset and not native_aux and name not in NATIVE_SOURCE_INCLUDES and p.suffix not in (".py", ".md", ".json", ".toml", ".c", ".h", ".asm", ".qc", ".patch") and name not in (".gitignore", ".gitattributes", "LICENSE", "VERSION", "CHIM_VERSION", "engine/aga/COPYING", "build.sh", "build.cmd", "build.ps1", "setup-windows.cmd", "setup-windows.ps1"):
            raise ValueError(f"Unexpected distributable file type: {name}")
    return sorted(paths)


def version(root):
    return public_version(root)


# Inherited files (original id Software/AmiQuake sources, licence texts) keep their historical
# formatting while they are byte-identical to the last PUBLISHED release. The list is keyed to that
# release's commit, not to the VERSION being worked on, so a new VERSION needs no extra file.
WHITESPACE_BASELINE = 'docs/WHITESPACE-BASELINE.json'
# Only inherited code lives here (id Software/AmiQuake engine, QuakeC, upstream patches and licence
# texts); project-authored files elsewhere are never exempt, whatever the baseline lists.
INHERITED_PREFIXES = ('engine/aga/', 'docs/aga/')


def whitespace_defects(name, data):
    """Trailing spaces/tabs, whitespace-only lines, space before tab in indentation, blank EOF."""
    errors = []
    lines = data.splitlines()
    for number, line in enumerate(lines, 1):
        if line.endswith((b' ', b'\t')):
            errors.append(f'{name}:{number}: trailing whitespace')
        indent = re.match(rb'^[ \t]*', line).group()
        if b' \t' in indent:
            errors.append(f'{name}:{number}: space before tab in indentation')
    if lines and not lines[-1].strip():
        errors.append(f'{name}:{len(lines)}: blank line at EOF')
    return errors


def load_whitespace_baseline(root):
    """The published-release baseline record, or None when the file is absent."""
    path = root / WHITESPACE_BASELINE
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding='utf-8'))
    files = record.get('files') if isinstance(record, dict) else None
    if (not isinstance(files, dict) or not isinstance(record.get('release'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', str(record.get('commit', '')))
            or not all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{64}', v) for v in files.values())):
        raise ValueError(f'Invalid {WHITESPACE_BASELINE}: expected release, commit and files {{path: sha256}}')
    return record


def check_source_whitespace(root, content):
    """Block whitespace defects before checking or packaging changed source.

    Files under INHERITED_PREFIXES that are byte-identical to the last published release (listed
    in docs/WHITESPACE-BASELINE.json) retain their historical formatting. Every other text file,
    including an inherited file we edit and untracked files in an extracted ZIP, is checked in full.
    """
    record = load_whitespace_baseline(root)
    exempt = record['files'] if record else {}
    errors = []
    for name, data in content.items():
        if name in DOCUMENTATION_IMAGES or name in DOCUMENTATION_CLIPS or name in PROJECT_MEDIA:
            continue
        if name.startswith(INHERITED_PREFIXES) and exempt.get(name) == hashlib.sha256(data).hexdigest():
            continue
        errors.extend(whitespace_defects(name, data))
    if errors:
        if record is None:
            hint = (f'{WHITESPACE_BASELINE} is missing, so no inherited file is exempt. Write it from the '
                    'last published release (its tag must be present): '
                    'python3 tools/release.py --whitespace-baseline v<LAST PUBLISHED VERSION>')
        else:
            hint = (f'{len(exempt)} inherited files of published v{record["release"]} '
                    f'({record["commit"][:12]}) are exempt while byte-identical; a file you edit is '
                    'checked in full, so clean the whole file. Our own files are never exempt.')
        raise ValueError('Source whitespace check failed:\n' + '\n'.join(errors) + '\n' + hint)


def whitespace_baseline_record(blobs, commit, tagged, revision='HEAD'):
    """Baseline record from a release tree ({path: bytes}); tagged = commit its v<VERSION> tag names."""
    if 'VERSION' not in blobs:
        raise ValueError(f'{revision} has no VERSION file')
    release_version = blobs['VERSION'].decode('ascii').strip()
    if tagged != commit:
        raise ValueError(f'{revision} ({commit[:12]}) is not the published release: tag v{release_version} '
                         f'must point to it (found {tagged[:12] or "no tag"}). Fetch the tags first.')
    files = {}
    for name, data in blobs.items():
        if not name.startswith(INHERITED_PREFIXES) or b'\0' in data or PurePosixPath(name).suffix in ('.png', '.gif'):
            continue
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if whitespace_defects(name, data):
            files[name] = hashlib.sha256(data).hexdigest()
    return {'note': ('Inherited files (engine/aga/, docs/aga/) of the last published release that keep '
                     'their historical whitespace while byte-identical (tools/release.py '
                     'check_source_whitespace). Written by python3 tools/release.py --whitespace-baseline '
                     'v<VERSION> after a release is published; a newer release can only shrink this list.'),
            'release': release_version, 'commit': commit, 'files': dict(sorted(files.items()))}


def whitespace_baseline(root, revision):
    """Read a published release commit with git and build its baseline record."""
    def git(*args, data=None):
        return subprocess.check_output(['git', '-C', str(root), *args], input=data)
    commit = git('rev-parse', '--verify', revision + '^{commit}').decode().strip()
    rows = [r for r in git('ls-tree', '-r', '-z', commit).split(b'\0') if r]
    meta = []
    for row in rows:
        info, name = row.split(b'\t', 1)
        _mode, kind, oid = info.decode('ascii').split()
        if kind == 'blob':
            meta.append((name.decode('utf-8'), oid))
    out = git('cat-file', '--batch', data=''.join(oid + '\n' for _, oid in meta).encode('ascii'))
    blobs, pos = {}, 0
    for name, oid in meta:
        newline = out.index(b'\n', pos)
        found, _kind, size = out[pos:newline].decode('ascii').split()
        if found != oid:
            raise ValueError('Unexpected git object for ' + name)
        blobs[name] = out[newline + 1:newline + 1 + int(size)]
        pos = newline + 1 + int(size) + 1
    tagged = ''
    if 'VERSION' in blobs:
        try:
            tag = 'v' + blobs['VERSION'].decode('ascii').strip()
            tagged = git('rev-parse', '--verify', '--quiet', tag + '^{commit}').decode().strip()
        except subprocess.CalledProcessError:
            tagged = ''
    return whitespace_baseline_record(blobs, commit, tagged, revision)


def write_whitespace_baseline(root, revision):
    record = whitespace_baseline(root, revision)
    with (root / WHITESPACE_BASELINE).open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
    return {'baseline': WHITESPACE_BASELINE, 'release': record['release'], 'commit': record['commit'],
            'inherited_files': len(record['files'])}


def inspect_source(root):
    if (root / 'engine/aga').exists():
        check_native_versions(root)
    allowed = allowed_files(root)
    # A ZIP may include an image that git add silently ignores. Require the
    # repository's explicit per-media exception alongside the package allowlist.
    media = set(allowed) & (DOCUMENTATION_IMAGES | DOCUMENTATION_CLIPS | PROJECT_MEDIA)
    if media:
        ignore = (root / '.gitignore').read_text().splitlines() if (root / '.gitignore').is_file() else []
        exceptions = {line[1:].lstrip('/') for line in ignore if line.startswith('!')}
        missing = sorted(media - exceptions)
        if missing:
            raise ValueError('Public media lacks explicit gitignore exception: ' + ', '.join(missing))
    found = set()
    for path in root.rglob("*"):
        parts = path.relative_to(root).parts
        if parts[0] == "out":
            continue  # Ignored private build outputs are never source-package inputs.
        if path.relative_to(root).as_posix() == "docs/PACKAGE_MANIFEST.json":
            continue  # Packaging receipt, regenerated rather than redistributed as source.
        if any(p in IGNORED_PARTS or p.endswith(".egg-info") for p in parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Source symlink is not allowed: {path.relative_to(root)}")
        if path.is_file():
            found.add(path.relative_to(root).as_posix())
    if found != set(allowed):
        raise ValueError(f"Source file list mismatch. Unexpected: {sorted(found-set(allowed))}; missing: {sorted(set(allowed)-found)}")
    if (root / ".git").exists():
        tracked = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
        if any(p and p not in allowed for p in tracked):
            raise ValueError("Git tracks files outside the release file list")
    content = {}
    for name in allowed:
        data = (root / name).read_bytes()
        if name in DOCUMENTATION_CLIPS:
            if not data.startswith((b'GIF87a', b'GIF89a')) or len(data) > 4194304:
                raise ValueError(f"Invalid public GIF: {name}")
            content[name] = data
            continue
        if name in DOCUMENTATION_IMAGES or name in PROJECT_MEDIA:
            limit = 2097152 if name in PROJECT_MEDIA else 1048576
            if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) > limit:
                raise ValueError(f"Invalid public PNG: {name}")
            content[name] = data
            continue
        if len(data) > text_limit(name) or b"\0" in data:
            raise ValueError(f"Unexpected binary or oversized source content: {name}")
        data.decode("utf-8")
        content[name] = data
    check_source_whitespace(root, content)
    return content


def create_candidate(root, path):
    content = inspect_source(root)
    ver = version(root)
    manifest = {"project": PROJECT, "version": ver,
                "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                          for name, data in content.items()}}
    payload = dict(content)
    payload["docs/PACKAGE_MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True)+"\n").encode()
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH', str(int((root/'VERSION').stat().st_mtime))))
    stamp = datetime.fromtimestamp(epoch, timezone.utc)
    if not 1980 <= stamp.year <= 2107:
        raise ValueError('ZIP timestamp must be in 1980..2107')
    zip_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second // 2 * 2)
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(f"{PROJECT}/{name}", date_time=zip_time)
            info.create_system = 3
            info.external_attr = (0o100755 if name in EXECUTABLES else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload[name], compresslevel=9)
    return manifest


def validate_candidate(root, archive_path):
    # Re-read source independently of the packing operation.
    content = inspect_source(root)
    manifest_name = f"{PROJECT}/docs/PACKAGE_MANIFEST.json"
    expected = {f"{PROJECT}/{p}" for p in content} | {manifest_name}
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Candidate archive contains unexpected or duplicate paths")
        if archive.testzip() is not None:
            raise ValueError("Candidate CRC failure")
        manifest = json.loads(archive.read(manifest_name))
        if manifest.get("version") != version(root) or manifest.get("project") != PROJECT:
            raise ValueError("Candidate version mismatch")
        if set(manifest["files"]) != set(content):
            raise ValueError("Candidate manifest path mismatch")
        for name, data in content.items():
            actual = archive.read(f"{PROJECT}/{name}")
            mode = archive.getinfo(f"{PROJECT}/{name}").external_attr >> 16
            if (mode & 0o777) != (0o755 if name in EXECUTABLES else 0o644):
                raise ValueError(f"Candidate permission mismatch: {name}")
            record = manifest["files"][name]
            if actual != data or record != {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}:
                raise ValueError(f"Candidate content mismatch: {name}")
    return {"status": "passed", "source_files": len(content), "version": version(root)}


def release(root, workspace):
    workspace = ensure_external(workspace, "release workspace")
    incoming, releases = workspace / "incoming", workspace / "releases"
    incoming.mkdir(parents=True, exist_ok=True)
    releases.mkdir(parents=True, exist_ok=True)
    name = f"AmiWind-v{version(root)}-public-source.zip"
    final = releases / name
    checksum = releases / (name + ".sha256")
    if final.exists() or checksum.exists():
        raise ValueError("This release version already exists. Existing releases are immutable; bump the version.")
    with tempfile.TemporaryDirectory(prefix="source-", dir=incoming) as tmp:
        candidate = Path(tmp) / name
        create_candidate(root, candidate)
        result = validate_candidate(root, candidate)
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        with final.open("xb") as dst, candidate.open("rb") as src:
            shutil.copyfileobj(src, dst)
        with checksum.open("x", encoding="utf-8", newline="\n") as dst:
            dst.write(f"{digest}  {name}\n")
    return {**result, "archive": str(final), "checksum": str(checksum), "sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--check", action="store_true", help="Inspect the source file list without creating a release")
    parser.add_argument("--whitespace-baseline", metavar="RELEASE_TAG",
                        help="Write docs/WHITESPACE-BASELINE.json from a published release tag (e.g. v0.0.32)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.whitespace_baseline:
            print(json.dumps(write_whitespace_baseline(root, args.whitespace_baseline), indent=2))
        elif args.check:
            print(json.dumps({"source_files": len(inspect_source(root)), "status": "passed"}, indent=2))
        elif args.workspace:
            print(json.dumps(release(root, args.workspace), indent=2))
        else:
            parser.error("Choose --check or --workspace PATH")
    except (ValueError, OSError, UnicodeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
