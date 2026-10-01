#!/usr/bin/env python3
"""Compare detected tool versions with the recorded reference environment."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
from build_host import find_executable

REFERENCE = Path(__file__).with_name("build-reference.json")


def find_qcc(args):
    """An explicit compiler always wins; otherwise prefer the reference tool."""
    if args.qcc:
        return args.qcc
    candidates = [args.tools_dir / 'Quake-Tools/qcc-host', 'qcc-host', 'qcc', 'fteqcc']
    return next((found for value in candidates if (found := find_executable(value))), None)


def find_quake_tools(args):
    if args.quake_tools:
        return args.quake_tools.expanduser().resolve()
    candidate = args.tools_dir / 'ericw/bin'
    return candidate.resolve() if all(find_executable(candidate/name) for name in ('qbsp', 'vis', 'light')) else None


def compare(detected, reference):
    if detected is None:
        return "missing"
    if detected == reference:
        return "matching"
    # Order release numbers; do not guess equivalence/order for vendor or
    # prerelease suffix changes on the same numeric release.
    pattern = r"^(\d+(?:\.\d+)*)(.*)$"
    left, right = re.fullmatch(pattern, detected), re.fullmatch(pattern, reference)
    if not left or not right:
        return "unknown"
    a, b = tuple(map(int, left[1].split('.'))), tuple(map(int, right[1].split('.')))
    width = max(len(a), len(b))
    a, b = a + (0,) * (width-len(a)), b + (0,) * (width-len(b))
    if a != b:
        return "newer" if a > b else "older"
    return "unknown"


def probe(name, value, spec):
    path = find_executable(value)
    row = {"name": name, "reference": spec["version"], "detected": None, "status": "missing"}
    if not path:
        return row
    path = str(Path(path).resolve())
    row["path"] = path
    row["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if "sha256" in spec:
        row.update(detected="sha256:" + row["sha256"],
                   status="matching" if row["sha256"] == spec["sha256"] else "unknown")
        if name == 'qcc' and Path(path).name.lower().startswith('fteqcc'):
            row.update(detected="FTEQCC; alternative compiler (not the id qcc reference)", status="alternative")
        return row
    try:
        # Some older tools print their banner and reject --version. Isolate
        # probes so incidental log files cannot dirty the checkout/game tree.
        with tempfile.TemporaryDirectory(prefix="amiwind-version-") as temp:
            result = subprocess.run([path, *spec["arguments"]], cwd=temp,
                                    stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, errors="replace", timeout=10)
        if spec.get('availability_only'):
            available = result.returncode == 0 and 'usage:' in (result.stdout + result.stderr).lower()
            row.update(status='available' if available else 'unknown',
                       detected='help works; CLI has no version flag; see amitools package above'
                       if available else 'help probe failed')
            return row
        match = re.search(spec["pattern"], result.stdout + result.stderr)
        row["detected"] = match[1].strip() if match else "unrecognized banner"
        row["status"] = compare(row["detected"], spec["version"])
    except (OSError, subprocess.SubprocessError) as exc:
        row.update(status="unknown", detected="probe failed: " + str(exc))
    return row


def report(args, tools=None):
    reference = json.loads(REFERENCE.read_text())
    rows = [{"name": "Python", "kind": "interpreter", "detected": platform.python_version(),
             "reference": reference["python"],
             "status": compare(platform.python_version(), reference["python"])}]
    for name, version in reference["packages"].items():
        try:
            detected = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            detected = None
        rows.append({"name": name, "kind": "package", "detected": detected, "reference": version,
                     "status": compare(detected, version)})
    values = dict(tools or {})
    for name in ("make", "cc", "ffmpeg", "xdftool", "rdbtool"):
        values.setdefault(name, getattr(args, name, name))
    for name in ("m68k-amigaos-gcc", "vasmm68k_mot"):
        value = args.sdk / "bin" / name if args.sdk else name
        if name == "vasmm68k_mot" and args.vasm:
            value = args.vasm
        values.setdefault(name, value)
    map_dir = find_quake_tools(args)
    for name in ("qbsp", "vis", "light"):
        values.setdefault(name, map_dir / name if map_dir else name)
    values.setdefault("qcc", find_qcc(args))
    for name, spec in reference["tools"].items():
        rows.append({**probe(name, values.get(name), spec), "kind": "tool"})
    print("Versions compared with the recorded Linux reference:")
    for row in rows:
        print(f"  [{row['status']}] {row['name']}: {row['detected'] or 'not found'} (reference {row['reference']})")
        if row.get('path'):
            print(f"    {row['path']}")
    print("Matching identifies the recorded version, not proof that this machine builds successfully.")
    print("Newer/older/unknown/alternative versions need validation; see docs/BUILD_DEPENDENCIES.md.")
    return rows
