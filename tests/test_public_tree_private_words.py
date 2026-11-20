# SPDX-License-Identifier: GPL-3.0-only
"""The public tree's file list for the tree-wide checks (tests/test_public_tree_tracking_links.py imports it).

Until v0.0.67 this test also refused, on every commit, the names of the private working folder and of tools the
public text never names, assistant instruction files and the private channels, with its word lists kept in pieces
in the public code. Decided for the project, 19 November 2026: those lists do not belong in the public tree at all,
not even in pieces. The same checks run in the maintainer's own tooling instead: the privacy step that opens every
gate and the release guard read every file and folder name and every file's bytes of the whole public tree."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def public_files():
    listed = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
    try:
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, check=True)
        listed = sorted(set(listed) | {p for p in tracked.stdout.decode('utf-8').split('\0') if p})
    except (OSError, subprocess.CalledProcessError):
        pass                               # a source tree without git (a release ZIP): the public list alone
    return listed
