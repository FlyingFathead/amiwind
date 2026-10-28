# SPDX-License-Identifier: GPL-3.0-only
"""Public prose names the project's maintainer as "the maintainer", never "the owner".

A decision made for the project reads "project decision" / "decided for the project"; a person who
acts (reports, plays, decides, publishes, approves) is "the maintainer". Technical ownership stays:
the owner chunk / frame / core / record of a placement, cell and town ownership, storage owners,
the schema field owner_accepted, status values such as owner-accepted-known-findings, the reporter
value "owner" in bugs.json and bug IDs.

Not checked: frozen history (docs/journals/, the bug archive, released notes and whitespace baselines in
docs/releases/, the records and superseded documents in docs/history/), the generated register pages
(their live rows come from bugs.json, checked below; archived rows from the frozen archive), recorded
receipts (docs/validation/, the build receipts copied into the Toolkit's CHIM inclusion ledger), the
generated blocks of bug pages (rendered from bugs.json or the frozen archive), engine source comments,
code spans, link targets and the technical uses listed in TECHNICAL_LINES.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_DEV_NOTES = re.compile(r'^docs/releases/notes/RELEASE-v0\.0\.42')
SKIP = re.compile(r'^(docs/journals/|docs/bugs/archive/|engine/|src/|docs/releases/|docs/history/|docs/validation/|'
                  r'docs/BUGS\.md$|docs/bugs/CHIM_TRACKER\.md$|amiwind-toolkit/chim-inclusion\.js(on)?$|'
                  r'tests/test_maintainer_wording\.py$)')
TEXT = {'.md', '.json', '.py', '.sh', '.js', '.html', '.txt', '.c', '.h', '.yml', '.ps1', '.cmd'}
# Words after "the owner" that make it technical (ownership of chunks, frames, cells, records ...).
TECHNICAL = ('chunk', 'chunks', 'frame', 'frames', 'core', 'cores', 'record', 'records', 'field', 'region',
             'regions', 'cell', 'cells', 'of', 'apron', 'aprons', 'backlink', 'backlinks')
NOT_AFTER = r"(?<![-'\"\w])"
PERSON = re.compile(
    r"\b[Tt]he owner(?:'s)?\b(?! (?:%s)\b)" % '|'.join(TECHNICAL)
    + r"|" + NOT_AFTER + r"[Oo]wner (?:decisions?|acceptance|reports?|reported|playtests?|playtesting|order"
    r"|rules?|requirements?|screenshots?|evidence|confirms|confirmed|confirmation|requests?|requested|approval"
    r"|approved|feedback|review|direction|priority|choice|follow-up|instruction)\b"
    r"|" + NOT_AFTER + r"[Oo]wner-(?:accepted|approved|reported|requested|supplied|provided|run|tested"
    r"|confirmed|selected|visible|deferred|directed|required)\b(?![-\w])")
# "the owner" lines that are technical (a chunk, path, harvest slot or placement owner), by file.
TECHNICAL_LINES = {
    'docs/chim/WORLD_FORMAT.md': ('chunks other than the owner also need',),
    'tools/chim/apron_policy.py': ("Reuse the owner's exact compiled render",),
    'tests/aga_chim_world_test.c': ('drawn by exactly one chunk, the owner', 'the owner takes over its placement',
                                    'the hole the owner fell through'),
    'tests/aga_harvest_compact_test.c': ('empties the owner and releases',),
    'tests/aga_npcpath_test.c': ("the owner's step", 'the owner teleports'),
}
GENERATED = re.compile(r'<!-- BEGIN GENERATED .*?<!-- END GENERATED [A-Z]+ -->', re.S)
MASK = re.compile(r'`[^`\n]*`|\]\([^)\s]*\)|https?://\S+')
# Live register prose fields that are rendered as words (bugs.json; reporter values stay data).
PROSE_FIELDS = ('title', 'status', 'severity_reason', 'where', 'persists_in')


def public_files():
    for rel in json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')):
        if SKIP.match(rel) and not CURRENT_DEV_NOTES.match(rel):
            continue
        p = ROOT / rel
        if p.suffix in TEXT and p.is_file():
            yield rel, p


def blank(m):
    return '\n' * m.group(0).count('\n')


def hits(text, allowed=()):
    out = []
    for n, line in enumerate(text.split('\n'), 1):
        if any(a in line for a in allowed):
            continue
        for m in PERSON.finditer(MASK.sub(' ', line)):
            out.append((n, m.group(0)))
    return out


class MaintainerWordingTest(unittest.TestCase):
    def test_pattern(self):
        self.assertTrue(hits('Reported by the owner in play.'))
        self.assertTrue(hits('An owner decision, 9 October 2026.'))
        self.assertTrue(hits("the owner's playtest"))
        self.assertTrue(hits('an owner-approved reason'))
        self.assertFalse(hits('the owner chunk of a placement; cell ownership; owner_accepted'))
        self.assertFalse(hits('see `the owner` in code and [x](#owner-decision-1)'))
        self.assertFalse(hits("status 'owner-accepted-known-findings', flag --owner-accepted"))

    def test_public_prose(self):
        bad = []
        for rel, p in public_files():
            try:
                text = p.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if rel.startswith('docs/bugs/'):
                text = GENERATED.sub(blank, text)
            bad += ['%s:%d: %s' % (rel, n, w) for n, w in hits(text, TECHNICAL_LINES.get(rel, ()))]
        self.assertEqual(bad, [], 'use "the maintainer" (a person acting) or "the project" (a decision) in '
                                  'public prose; "owner" stays only for technical ownership')

    def test_live_register(self):
        bad = []
        for b in json.loads((ROOT / 'docs' / 'bugs' / 'bugs.json').read_text(encoding='utf-8')):
            texts = [b.get(k) for k in PROSE_FIELDS] + [r.get('note') for r in b.get('reports') or []]
            if isinstance(b.get('build'), dict):
                texts += [v for v in b['build'].values() if isinstance(v, str)]
            for t in texts:
                if isinstance(t, str):
                    bad += ['%s: %s' % (b['id'], w) for _, w in hits(t)]
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
