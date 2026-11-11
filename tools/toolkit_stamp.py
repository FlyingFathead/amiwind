# SPDX-License-Identifier: GPL-3.0-only
"""The small version stamp the served Toolkit answers at /amiwind-toolkit/version.json.

The pages poll it every half minute (amiwind-toolkit/auto-refresh.js) and reload themselves, keeping the viewer's
state, when it changes. The stamp holds what a viewer would want to be on the newest of:

  commit   the commit the Toolkit files are served from: the checkout's own HEAD, or, in follow mode, the head the
           published working-version record names
  version  the AmiWind version of that line (the record's working_version, else the VERSION file)
  line     the Toolkit's own version and its "Last updated with AmiWind" line
  ingest   when the CHIM tracker data was last written (its modification time and size)
  follow   true when the server follows a published record

Standard library only. The same file is used by the public and the private server; the private launcher only passes
the record's path (toolkit_serve.py --follow RECORD).
"""
import json
import re
import subprocess
from pathlib import Path

FORMAT = 'aw-toolkit-stamp-1'
WATCHED = ('commit', 'version', 'line', 'ingest')      # a change in any of these reloads the page
OWN_RE = re.compile(r"const TOOLKIT = \{name: '[^']*', version: '([0-9.]+)'")
LINE_RE = re.compile(r"Last updated with AmiWind (v[0-9][0-9.]*)")


def read_record(path):
    """{'head', 'version'} from a published working-version record (a JSON file with "head" and "working_version"), or None."""
    try:
        doc = json.loads(Path(path).read_text(encoding='utf-8'))
        head = str(doc.get('head') or '').strip()
        return {'head': head, 'version': str(doc.get('working_version') or '').strip()} if head else None
    except (OSError, ValueError, AttributeError):
        return None


def git(root, *args):
    """stdout of a git command in root, or None."""
    try:
        done = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def resolve_commit(root, ref):
    """The full commit a ref or abbreviated head names in root's repository, or None."""
    out = git(root, 'rev-parse', '--verify', '-q', str(ref) + '^{commit}')
    return out.strip() if out and out.strip() else None


def file_at(root, commit, path):
    """The bytes of a repository file at a commit (git show), or None; never reads outside the repository."""
    try:
        done = subprocess.run(['git', '-C', str(root), 'show', '%s:%s' % (commit, path)], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def read_file(root, relpath, commit=None):
    """A repository file's text: at `commit` in follow mode, else from the checkout. None when absent."""
    if commit:
        raw = file_at(root, commit, relpath)
        return raw.decode('utf-8', 'replace') if raw is not None else None
    try:
        return (Path(root) / relpath).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


def ingest_mark(progress_dir):
    """(mtime, size) of the tracker data file, or None when there is none."""
    if not progress_dir:
        return None
    p = Path(progress_dir)
    p = p if p.is_file() else p / 'cell-progress.json'
    try:
        st = p.stat()
    except OSError:
        return None
    return {'mtime': int(st.st_mtime), 'size': st.st_size}


def make_stamp(root, record=None, progress_dir=None):
    """The stamp document. record = path of the published record to follow, or None (the checkout's own HEAD)."""
    follow = None
    if record:
        rec = read_record(record)
        commit = resolve_commit(root, rec['head']) if rec else None
        follow = {'record': rec, 'resolved': bool(commit)}
    else:
        rec, commit = None, None
    if not commit:
        head = git(root, 'rev-parse', 'HEAD')
        commit = head.strip() if head else None
        followed_commit = None
    else:
        followed_commit = commit
    version = (rec or {}).get('version') or (read_file(root, 'VERSION', followed_commit) or '').strip() or None
    world = read_file(root, 'amiwind-toolkit/world-map.html', followed_commit) or ''
    header = read_file(root, 'amiwind-toolkit/header.js', followed_commit) or ''
    own, line = OWN_RE.search(world), LINE_RE.search(header)
    return {'format': FORMAT, 'commit': commit, 'version': version, 'follow': bool(record),
            'line': {'toolkit': own.group(1) if own else None, 'last_updated_with': line.group(1) if line else None},
            'ingest': ingest_mark(progress_dir), 'followed_commit': followed_commit,
            'note': (follow or {}).get('resolved') is False and 'the record names a commit this checkout does not have' or None}


def changed(old, new):
    """True when the viewer is looking at something older than `new`. A missing or unreadable stamp never reloads."""
    if not isinstance(old, dict) or not isinstance(new, dict) or new.get('format') != FORMAT:
        return False
    return any(old.get(k) != new.get(k) for k in WATCHED)
