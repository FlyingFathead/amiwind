"""Keep private data outside distributable source; /out is the ignored build area."""
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def source_root():
    root = Path(__file__).resolve().parents[2]
    return root if (root / "pyproject.toml").is_file() else None


def inside(path, root):
    return path == root or root in path.parents


def ensure_external(path, label="path"):
    lexical = Path(os.path.abspath(Path(path).expanduser()))
    resolved = lexical.resolve()
    root = source_root()
    for candidate in (lexical, resolved):
        if root and inside(candidate, root) and not inside(candidate, root / "out"):
            raise ValueError(f"{label} must be outside the source repository: {path}")
        for parent in (candidate, *candidate.parents):
            project = parent / "pyproject.toml"
            if project.is_file() and project.stat().st_size < 65536:
                text = project.read_text(encoding="utf-8", errors="replace")
                if 'name = "amiwind"' in text and inside(candidate, parent / "out"):
                    continue
                if any('name = "'+name+'"' in text for name in ("amiwind", "morrowind-amiga-demake")):
                    raise ValueError(f"{label} must be outside AmiWind source checkouts: {path}")
    return resolved


def child_ci(parent, name, required=True):
    matches = [p for p in parent.iterdir() if p.name.casefold() == name.casefold()]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous filename differing only by case: {name}")
    if not matches:
        if required:
            raise ValueError(f"Missing {name} in {parent}")
        return None
    return ensure_external(matches[0], name)


def is_wsl():
    return sys.platform == "linux" and bool(os.environ.get("WSL_DISTRO_NAME") or
                                            "microsoft" in platform.release().lower())


def installed_game_path(path):
    """Accept a pasted Windows drive path when running inside WSL."""
    text = str(path).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    if sys.platform != "win32" and re.match(r"^[A-Za-z]:[\\/]", text):
        if not is_wsl():
            raise ValueError("Windows drive path supplied outside Windows/WSL; supply its Linux mount path")
        try:
            text = subprocess.check_output(["wslpath", "-u", text], text=True,
                                           stderr=subprocess.PIPE, timeout=10).strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("Cannot translate the Windows path with wslpath; supply the mounted Linux path") from exc
        if not text.startswith("/"):
            raise ValueError("wslpath did not return an absolute Linux path")
    return Path(text)


def resolve_data_files(path):
    path = installed_game_path(path)
    path = ensure_external(path, "game input")
    if not path.is_dir():
        raise ValueError(f"Game input is not a directory: {path}")
    if child_ci(path, "Morrowind.esm", required=False) is None:
        path = child_ci(path, "Data Files")
    for name in ("Morrowind.esm", "Morrowind.bsa"):
        if not child_ci(path, name).is_file():
            raise ValueError(f"Expected a regular file: {name}")
    return path


def init_workspace(path):
    path = ensure_external(path, "workspace")
    if path.exists():
        raise ValueError("Workspace path already exists; choose a new dedicated directory")
    path.mkdir(parents=True)
    for name in ("original", "generated", "previews", "build", "cache", "incoming", "releases"):
        (path / name).mkdir()
    (path / "workspace.json").write_text(json.dumps({"format": 1, "project": "amiwind"}, indent=2)+"\n", encoding="utf-8")
    return {"workspace": str(path), "original_data": str(path / "original" / "Data Files")}


def read_workspace(path):
    path = ensure_external(path, "workspace")
    config = ensure_external(path / "workspace.json", "workspace configuration")
    if not config.is_file():
        raise ValueError("Not a configured workspace; run setup first")
    state = json.loads(config.read_text(encoding="utf-8"))
    if state.get("project") not in ("amiwind", "morrowind-amiga-demake") or state.get("format") != 1:
        raise ValueError("Unrecognized workspace configuration")
    return path, state


def setup_workspace(path, data_files, target):
    data_files = resolve_data_files(data_files)
    path = ensure_external(path, "workspace")
    if not path.exists():
        init_workspace(path)
    path, state = read_workspace(path)
    if target not in ("a500", "a1200"):
        raise ValueError("Unknown target profile")
    state.update({"data_files": str(data_files), "target": target})
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path, delete=False) as tmp:
        tmp.write(json.dumps(state, indent=2)+"\n")
        temporary = Path(tmp.name)
    temporary.replace(path / "workspace.json")
    return {"workspace": str(path), "data_files": str(data_files), "target": target,
            "status": "configured", "conversion_scope": "exterior terrain proof of concept"}
