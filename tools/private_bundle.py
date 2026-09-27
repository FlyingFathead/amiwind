#!/usr/bin/env python3
"""Create a PRIVATE development bundle containing the owner's original game data.

This is not a public source release. The public source archive must pass its
independent validation before it can be included as a separate sibling tree.
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mwad.paths import ensure_external, inside, read_workspace, resolve_data_files
from release import PROJECT, validate_candidate, version


def bundle(source_archive, workspace, destination):
    root = Path(__file__).resolve().parents[1]
    source_archive = ensure_external(source_archive, "public source archive")
    workspace, state = read_workspace(workspace)
    original = resolve_data_files(Path(state["data_files"]))
    destination = ensure_external(destination, "private bundle")
    roots = [(original, "original/Data Files")]
    for name in ("generated", "previews"):
        p = workspace / name
        if p.exists():
            roots.append((ensure_external(p, name), name))
    if any(inside(destination, p) for p, _ in roots):
        raise ValueError("Private bundle cannot be written inside an included data directory")
    checksum = destination.with_name(destination.name + ".sha256")
    if destination.exists() or checksum.exists():
        raise ValueError("Private bundle already exists; choose a new filename")
    validate_candidate(root, source_archive)
    files = []
    for folder, label in roots:
        for p in sorted(folder.rglob("*")):
            if p.is_symlink():
                raise ValueError("Private bundle does not follow source-data symlinks")
            if p.is_file():
                p = ensure_external(p, "private data")
                files.append((p, f"morrowind-amiga-workspace/{label}/{p.relative_to(folder).as_posix()}"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"{PROJECT}-private-{version(root)}/"
    quickstart = """# Private development bundle

This bundle contains the owner's original Morrowind files and locally generated
data. Keep it for private development. It is separate from the public source ZIP.

The two sibling folders are:
- amiwind: checked source, with no game assets inside it.
- morrowind-amiga-workspace: original game data and generated prototype data.

After extraction, change into amiwind and run:

```sh
python tools/mwad.py setup --data-files "../morrowind-amiga-workspace/original/Data Files" --workspace "../morrowind-amiga-workspace" --target a500
python tools/mwad.py verify "../morrowind-amiga-workspace/generated/seyda-neen"
```

The included terrain output is already generated. To run a new conversion, use
`convert --workspace "../morrowind-amiga-workspace" --name another-experiment`.
Setup rewrites the local game path for this computer; no old machine paths are
stored in the bundled workspace configuration. There is no playable Amiga
executable yet. Read the source README and docs for scope and next steps.
"""
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        with zipfile.ZipFile(source_archive) as source:
            for item in source.infolist():
                out.writestr(prefix + item.filename, source.read(item))
        out.writestr(prefix + "README-PRIVATE.md", quickstart)
        out.writestr(prefix + "morrowind-amiga-workspace/workspace.json",
                     json.dumps({"format": 1, "project": PROJECT, "target": state.get("target", "a500")}, indent=2)+"\n")
        for name in ("build", "cache", "incoming", "releases"):
            out.writestr(prefix + f"morrowind-amiga-workspace/{name}/", b"")
        for path, arcname in files:
            out.write(path, prefix + arcname)
    with zipfile.ZipFile(destination) as check:
        if check.testzip() is not None:
            raise ValueError("Private bundle CRC failure")
        with zipfile.ZipFile(source_archive) as source:
            for item in source.infolist():
                if check.read(prefix + item.filename) != source.read(item):
                    raise ValueError("Private bundle source differs from the public source package")
    digest = hashlib.sha256()
    with destination.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            digest.update(block)
    with checksum.open("x", encoding="utf-8", newline="\n") as f:
        f.write(f"{digest.hexdigest()}  {destination.name}\n")
    result = {"private_bundle": str(destination), "bytes": destination.stat().st_size,
              "private_data_files": len(files), "checksum": str(checksum), "sha256": digest.hexdigest()}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        bundle(args.source_archive, args.workspace, args.out)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
