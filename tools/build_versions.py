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

REFERENCE = Path(__file__).with_name("build-reference.json")


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
    path = shutil.which(str(value)) if value else None
    row = {"name": name, "reference": spec["version"], "detected": None, "status": "missing"}
    if not path:
        return row
    row["path"] = str(Path(path).resolve())
    row["sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if "sha256" in spec:
        row.update(detected="sha256:" + row["sha256"],
                   status="matching" if row["sha256"] == spec["sha256"] else "unknown")
        return row
    try:
        # Some older tools print their banner and reject --version. Isolate
        # probes so incidental log files cannot dirty the checkout/game tree.
        with tempfile.TemporaryDirectory(prefix="amiwind-version-") as temp:
            result = subprocess.run([path, *spec["arguments"]], cwd=temp,
                                    stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, errors="replace", timeout=10)
        match = re.search(spec["pattern"], result.stdout + result.stderr)
        row["detected"] = match[1].strip() if match else "unrecognized banner"
        row["status"] = compare(row["detected"], spec["version"])
    except (OSError, subprocess.SubprocessError) as exc:
        row.update(status="unknown", detected="probe failed: " + str(exc))
    return row


def report(args, tools=None):
    reference = json.loads(REFERENCE.read_text())
    rows = [{"name": "Python", "detected": platform.python_version(),
             "reference": reference["python"],
             "status": compare(platform.python_version(), reference["python"])}]
    for name, version in reference["packages"].items():
        try:
            detected = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            detected = None
        rows.append({"name": name, "detected": detected, "reference": version,
                     "status": compare(detected, version)})
    values = dict(tools or {})
    for name in ("make", "cc", "ffmpeg", "xdftool", "rdbtool"):
        values.setdefault(name, getattr(args, name, name))
    for name in ("m68k-amigaos-gcc", "vasmm68k_mot"):
        value = args.sdk / "bin" / name if args.sdk else name
        if name == "vasmm68k_mot" and args.vasm:
            value = args.vasm
        values.setdefault(name, value)
    for name in ("qbsp", "vis", "light"):
        values.setdefault(name, args.quake_tools / name if args.quake_tools else name)
    values.setdefault("qcc", args.qcc or "qcc-host")
    for name, spec in reference["tools"].items():
        rows.append(probe(name, values.get(name), spec))
    print("Versions compared with the recorded Linux reference:")
    for row in rows:
        print(f"  [{row['status']}] {row['name']}: {row['detected'] or 'not found'} (reference {row['reference']})")
    print("Matching identifies the recorded version, not proof that this machine builds successfully.")
    print("Newer/older/unknown versions need validation; see docs/BUILD_DEPENDENCIES.md.")
    return rows
