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
PROJECT_MEDIA = {"resources/media/AmiWind_logo_clear_background.png", "resources/media/AmiWind_wordmark.png"}
IGNORED_PARTS = {".git", "__pycache__", ".venv", ".pytest_cache"}
DOCUMENTATION_IMAGES = {f"docs/images/amiwind-v0.0.15-dev2-{name}.png" for name in ("dock", "npc", "guard", "town", "waterfront")}
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev2-{name}.png" for name in ("port", "fargoth", "tradehouse", "prison"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev3-{name}.png" for name in ("rock-before", "rock-after", "dialogue"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.23-dev4-{name}.png" for name in ("dialogue", "darvame", "tree"))
DOCUMENTATION_IMAGES.add("docs/images/amiwind-v0.0.23-dev5-windows.png")
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc1-{name}.png" for name in ("balmora", "mages"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc2-{name}.png" for name in ("balmora-bridge", "balmora-street", "balmora-river"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc3-{name}.png" for name in ("dagoth", "balmora"))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-rc4-{name}.png" for name in ("map",))
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.24-{name}.png" for name in ("balmora-bridge", "balmora-street", "balmora-river", "dagoth", "map"))
DOCUMENTATION_IMAGES.add("docs/images/amiwind-v0.0.25-dev1-journal.png")
DOCUMENTATION_IMAGES.update(f"docs/images/amiwind-v0.0.25-rc1-{name}.png" for name in ("map", "navigation"))
DOCUMENTATION_CLIPS = {"docs/images/amiwind-v0.0.23-dev2-port.gif"}


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
        preset = (p.suffix in (".uae", ".fs-uae") and p.parent == PurePosixPath("resources/emulators")) or name in ("config/keymaps.cfg", "config/game.cfg") or name in DOCUMENTATION_IMAGES or name in DOCUMENTATION_CLIPS or name in PROJECT_MEDIA
        native_aux = name in ("engine/aga/Makefile", "engine/aga/qc/progs.src", "engine/aga/src/progdefs.q1", "engine/aga/src/progdefs.q2", "docs/aga/COPYING.NEWLIB", ".github/workflows/source-check.yml")
        if not preset and not native_aux and p.suffix not in (".py", ".md", ".json", ".toml", ".c", ".h", ".asm", ".qc", ".patch") and name not in (".gitignore", ".gitattributes", "LICENSE", "VERSION", "engine/aga/COPYING", "build.sh", "build.cmd", "build.ps1", "setup-windows.cmd", "setup-windows.ps1"):
            raise ValueError(f"Unexpected distributable file type: {name}")
    return sorted(paths)


def version(root):
    return public_version(root)


def check_source_whitespace(root, content):
    """Block whitespace defects before checking or packaging changed source.

    Exact unchanged base files retain their historical formatting. New/modified
    text files are checked in full, including untracked files in an extracted ZIP.
    """
    patch = root / 'docs' / f'PATCH-v{version(root)}.json'
    baseline = json.loads(patch.read_text()).get('base_files', {}) if patch.is_file() else {}
    errors = []
    for name, data in content.items():
        if name in DOCUMENTATION_IMAGES or name in DOCUMENTATION_CLIPS or name in PROJECT_MEDIA:
            continue
        if baseline.get(name, {}).get('sha256') == hashlib.sha256(data).hexdigest():
            continue
        lines = data.splitlines()
        for number, line in enumerate(lines, 1):
            if line.endswith((b' ', b'\t')):
                errors.append(f'{name}:{number}: trailing whitespace')
            indent = re.match(rb'^[ \t]*', line).group()
            if b' \t' in indent:
                errors.append(f'{name}:{number}: space before tab in indentation')
        if lines and not lines[-1].strip():
            errors.append(f'{name}:{len(lines)}: blank line at EOF')
    if errors:
        raise ValueError('Source whitespace check failed:\n' + '\n'.join(errors))


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
        if len(data) > 262144 or b"\0" in data:
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
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.check:
            print(json.dumps({"source_files": len(inspect_source(root)), "status": "passed"}, indent=2))
        elif args.workspace:
            print(json.dumps(release(root, args.workspace), indent=2))
        else:
            parser.error("Choose --check or --workspace PATH")
    except (ValueError, OSError, UnicodeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
