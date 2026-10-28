#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The docs/ index pages and the docs layout checks.

Usage:
  docs_index.py write    write docs/README.md, docs/releases/README.md and docs/history/README.md
  docs_index.py check    exit 1 if a page is stale, a document is missing from docs/README.topics.json, a
                         per-version file sits at the docs/ root, or a relative link points at no file
  docs_index.py links    print every broken relative link of the public documents (JSON)

docs/README.md is the index by topic: every document at the docs/ root with its title and its "Last updated" line,
and every docs/ folder. Its data is docs/README.topics.json (the topic of each document); a new document is not done
until it is listed there. docs/releases/README.md lists every release with its notes and whitespace baseline, and
maps the old docs/ root paths (GitHub has no redirects). docs/history/README.md lists the history records by kind
with their old paths (docs/history/MOVES.json).

Layout rule (in force from the v0.0.55 reorganisation): release notes go to docs/releases/notes/, whitespace
baselines to docs/releases/patches/, one-off records to docs/history/<kind>/, journals to docs/journals/; never a
per-version file at the docs/ root (PER_VERSION_ROOT).
"""
import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
TOPICS = 'docs/README.topics.json'
MOVES = 'docs/history/MOVES.json'
INDEX = 'docs/README.md'
RELEASES = 'docs/releases/README.md'
HISTORY = 'docs/history/README.md'
GH = 'https://github.com/FlyingFathead/amiwind'
INDEX_SELF = {'README.md', 'README.topics.json'}
# per-version and one-off record names that never sit at the docs/ root
PER_VERSION_ROOT = re.compile(r'^(RELEASE-|PATCH-|CHECKPOINT|LOCAL-|FEEDBACK-|INVESTIGATION-|VALIDATION-|PLAN-|MERGE-|'
                              r'RECONCILE|HORSTATORS|HEAP_CRASH|BALMORA-v|BUGS-v|RC\d+_|RECOVERY-|SHORELINE-)')
HISTORY_KINDS = [
    ('checkpoints', 'Checkpoint validations and release-candidate issue lists'),
    ('local-rc', 'Local release candidates and their recovery notes'),
    ('feedback', 'Playtest feedback of development builds'),
    ('investigations', 'Investigations and dated findings'),
    ('validation', 'Per-version and per-host validation records'),
    ('plans', 'Release plans'),
    ('merges', 'Merge and reconcile records'),
    ('other', 'Other early records'),
    ('superseded', 'Topic documents replaced by newer ones (each names its replacement)'),
]
LAST_UPDATED = re.compile(r'^_Last updated with AmiWind (v[^ ]+)(?: \(([^)]*)\))?\._', re.M)
GENERATED = re.compile(r'^_Generated from `[^`\n]+` with AmiWind (v[^ ]+)\._$', re.M)
VERSION_NAME = re.compile(r'^(?:RELEASE|PATCH)-v(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)-?(\d*)(?:-([a-z0-9-]+))?)?\.(?:md|json)$')
KIND_RANK = {'test': 0, 'dev': 1, 'rc': 2, None: 3}


def _generated_line(source):
    sys.path.insert(0, str(ROOT / 'tools'))
    from doc_toc import generated_line
    return generated_line(source)


def _read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def title_of(rel):
    if not rel.endswith('.md'):
        return posixpath.basename(rel)
    for line in _read(rel).splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return posixpath.basename(rel)


def updated_of(rel):
    if not rel.endswith('.md'):
        return 'data file'
    text = _read(rel)
    m = LAST_UPDATED.search(text)
    if m:
        return m.group(1) + (' (%s)' % m.group(2) if m.group(2) else '')
    m = GENERATED.search(text)
    if m:
        return 'generated (%s)' % m.group(1)
    return 'no line'


def cell(text):
    return text.replace('|', '\\|')


def topics():
    return json.loads(_read(TOPICS))


def root_docs():
    return sorted(p.name for p in DOCS.iterdir() if p.is_file() and p.name not in INDEX_SELF)


def doc_folders():
    return sorted(p.name for p in DOCS.iterdir() if p.is_dir())


def problems_topics(t=None):
    t = t or topics()
    listed = [d for topic in t['topics'] for d in topic['docs']]
    out = []
    for d in sorted(set(listed)):
        if listed.count(d) > 1:
            out.append('%s is listed under more than one topic' % d)
    present = set(root_docs())
    out += ['docs/%s is in no topic of %s: add it' % (d, TOPICS) for d in sorted(present - set(listed))]
    out += ['%s lists docs/%s, which does not exist' % (TOPICS, d) for d in sorted(set(listed) - present)]
    folders = [f['path'] for f in t['folders']]
    out += ['docs/%s/ is not in the folders of %s: add it' % (f, TOPICS) for f in doc_folders() if f not in folders]
    out += ['%s lists the folder docs/%s/, which does not exist' % (TOPICS, f) for f in folders if f not in doc_folders()]
    out += ['%s marks docs/%s for a refresh, which is in no topic' % (TOPICS, d) for d in t.get('refresh', []) if d not in listed]
    out += ['docs/%s: a per-version or one-off record at the docs/ root; it belongs in docs/releases/ or docs/history/'
            % d for d in sorted(present) if PER_VERSION_ROOT.match(d)]
    return out


def render_index():
    t = topics()
    refresh = set(t.get('refresh', []))
    out = ['# AmiWind documentation', '', _generated_line(TOPICS), '',
           'Every document of the project, by topic, with the version and date of its last update. A document marked '
           '"needs a refresh" predates the current state of its subject and is due for a review; its facts may be '
           'out of date. Release notes and whitespace baselines are listed in [releases](releases/README.md); '
           'one-off records and replaced documents in [history](history/README.md).', '']
    for topic in t['topics']:
        out += ['## %s' % topic['name'], '', '| Document | Title | Last updated |', '| --- | --- | --- |']
        for d in topic['docs']:
            upd = updated_of('docs/' + d)
            if d in refresh:
                upd += ', needs a refresh'
            out.append('| [%s](%s) | %s | %s |' % (d, d, cell(title_of('docs/' + d)), upd))
        out.append('')
    out += ['## Folders', '', '| Folder | What it holds | Start at |', '| --- | --- | --- |']
    for f in t['folders']:
        path = f['path']
        readme = DOCS / path / 'README.md'
        if readme.is_file():
            start = '[%s/README.md](%s/README.md)' % (path, path)
        else:
            mds = sorted(p.name for p in (DOCS / path).iterdir() if p.is_file() and p.suffix == '.md')
            start = ', '.join('[%s](%s/%s)' % (m, path, m) for m in mds) or 'data files only'
        out.append('| [%s/](%s/) | %s | %s |' % (path, path, cell(f['about']), start))
    return '\n'.join(out) + '\n'


def version_key(name):
    m = VERSION_NAME.match(name)
    if not m:
        return (0, 0, 0, -1, 0, name)
    kind = m.group(4)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), KIND_RANK.get(kind, 0), int(m.group(5) or 0), name)


def version_of(name):
    stem = name.split('-', 1)[1].rsplit('.', 1)[0]
    return stem


def render_releases():
    notes = sorted(p.name for p in (DOCS / 'releases' / 'notes').iterdir() if p.is_file())
    patches = sorted(p.name for p in (DOCS / 'releases' / 'patches').iterdir() if p.is_file())
    versions = {}
    for n in notes:
        versions.setdefault(version_of(n), {})['notes'] = n
    for p in patches:
        versions.setdefault(version_of(p), {}).setdefault('patches', []).append(p)
    rows = sorted(versions.items(), key=lambda kv: version_key('RELEASE-%s.md' % kv[0]), reverse=True)
    out = ['# AmiWind releases', '', _generated_line('docs/releases/'), '',
           'Every release line, newest first: its release notes (docs/releases/notes/) and the whitespace baseline '
           'of the published release it was built on (docs/releases/patches/). Until v0.0.54 these files sat at the '
           'docs/ root; the table at the end maps every old path to the new one. Links into an old release tag '
           '(%s/blob/v0.0.37/docs/releases/notes/RELEASE-v0.0.37.md) keep working, because every tag keeps its own tree.' % GH, '',
           '| Version | Kind | Title | Notes | Whitespace baseline | GitHub |', '| --- | --- | --- | --- | --- | --- |']
    for v, files in rows:
        m = VERSION_NAME.match('RELEASE-v%s.md' % v.lstrip('v')) if v.startswith('v') else None
        kind = (m.group(4) if m and m.group(4) else 'final') if m else 'record'
        note = files.get('notes')
        title = cell(title_of('docs/releases/notes/' + note)) if note else '-'
        note_link = '[%s](notes/%s)' % (note, note) if note else 'none'
        patch_link = ', '.join('[%s](patches/%s)' % (p, p) for p in files.get('patches', [])) or 'none'
        tag = '[tag %s](%s/releases/tag/%s)' % (v, GH, v) if kind == 'final' else '-'
        out.append('| %s | %s | %s | %s | %s | %s |' % (v, kind, title, note_link, patch_link, tag))
    out += ['', '## Old paths', '', 'GitHub has no redirects: a link to an old docs/ root path on the main branch '
            'finds nothing. The new place of every release file:', '', '| Old path (until v0.0.54) | New path |',
            '| --- | --- |']
    moves = json.loads(_read(MOVES))['moves']
    for old, new in sorted(moves.items()):
        if new.startswith('docs/releases/'):
            out.append('| `%s` | [%s](%s) |' % (old, new, posixpath.relpath(new, 'docs/releases')))
    return '\n'.join(out) + '\n'


def render_history():
    doc = json.loads(_read(MOVES))
    old_of = {new: old for old, new in doc['moves'].items()}
    out = ['# AmiWind history', '', _generated_line(MOVES), '',
           'Records of earlier work, kept as history and never deleted: each file sits in the folder of its kind. '
           'Nothing here describes the current state; the [documentation index](../README.md) does. '
           '[MOVES.json](MOVES.json) maps every file that left the docs/ root in v0.0.55 to its new place '
           '(release notes and baselines: [releases](../releases/README.md); journals: [journals](../journals/)).', '']
    for kind, about in HISTORY_KINDS:
        folder = DOCS / 'history' / kind
        if not folder.is_dir():
            continue
        out += ['## %s' % kind, '', about + '.', '', '| Document | Title | Old path |', '| --- | --- | --- |']
        for p in sorted(folder.iterdir(), key=lambda p: p.name):
            if not p.is_file():
                continue
            rel = 'docs/history/%s/%s' % (kind, p.name)
            out.append('| [%s](%s/%s) | %s | `%s` |' % (p.name, kind, p.name, cell(title_of(rel)), old_of.get(rel, rel)))
        out.append('')
    return '\n'.join(out).rstrip('\n') + '\n'


# the folder pages first: the index links each folder's README when it exists
PAGES = {RELEASES: render_releases, HISTORY: render_history, INDEX: render_index}

LINK = re.compile(r'\]\(<?([^)\s<>]+)>?(?:\s+"[^"]*")?\)')
REFDEF = re.compile(r'^ {0,3}\[[^\]\n]+\]:[ \t]*<?(\S+?)>?(?:[ \t]+"[^"\n]*")?[ \t]*$')
ATTR = re.compile(r'\b(?:src|href)="([^"]+)"')
SKIP = re.compile(r'^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|#|/)')


def public_markdown():
    files = json.loads(_read('tools/release-files.json'))
    return sorted(f for f in files if f.endswith('.md') and (ROOT / f).is_file())


def resolve(rel, target):
    """The repository path a relative link target names, or None for a link that is not a relative file link."""
    if SKIP.match(target):
        return None
    path = unquote(target.split('#', 1)[0].split('?', 1)[0])
    if not path:
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))


def broken_links():
    """[{"file", "target"}] for every relative link of the public documents that names no file or folder."""
    sys.path.insert(0, str(ROOT / 'tools'))
    from doc_toc import prose, CODE_SPAN
    out = []
    for rel in public_markdown():
        lines = _read(rel).splitlines()
        for _, line in prose(lines):
            line = CODE_SPAN.sub('', line)
            targets = [m.group(1) for m in LINK.finditer(line)] + [m.group(1) for m in ATTR.finditer(line)]
            m = REFDEF.match(line)
            if m:
                targets.append(m.group(1))
            for t in targets:
                path = resolve(rel, t)
                if path is None:
                    continue
                if path.startswith('..') or not (ROOT / path).exists():
                    out.append({'file': rel, 'target': path})
    features = ROOT / 'docs/chim/features.json'
    if features.is_file():
        for path in re.findall(r'"path":\s*"([^"#]+)', features.read_text(encoding='utf-8')):
            if not (ROOT / path).exists():
                out.append({'file': 'docs/chim/features.json', 'target': path})
    return sorted({(o['file'], o['target']) for o in out})


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ''
    if cmd == 'write':
        for rel, fn in PAGES.items():
            text = fn()
            (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
            with open(ROOT / rel, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(text)
            print('wrote %s' % rel)
        for p in problems_topics():
            print('PROBLEM ' + p)
        return 0
    if cmd == 'check':
        bad = problems_topics()
        for rel, fn in PAGES.items():
            if not (ROOT / rel).is_file() or (ROOT / rel).read_text(encoding='utf-8') != fn():
                bad.append('%s is stale: run python3 tools/docs_index.py write' % rel)
        for p in bad:
            print('FAIL ' + p)
        print('docs index: %s' % ('FAILED' if bad else 'current'))
        return 1 if bad else 0
    if cmd == 'links':
        print(json.dumps([{'file': f, 'target': t} for f, t in broken_links()], indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
