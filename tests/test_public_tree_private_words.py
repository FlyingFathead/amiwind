# SPDX-License-Identifier: GPL-3.0-only
"""No private folder, tool name or assistant instruction file in the public tree (the gate, every commit).

The maintainer, 24 October 2026: "ADD A GATE GUARD TO STOP ... directories or ... ANY FILE to be in the public repo",
and the instruction files are not allowed either. A register note named a private notes folder; only the release
guard, at the very end of the release flow, caught it. This test runs in the gate on every commit: every file of the
public file list (tools/release-files.json) and every file git tracks is checked by its path and by its bytes (text or
binary, any case) for the names of the private working folder and of tools the public text never names, and by its
file name for assistant instruction files. The words and names are kept in pieces here so this file holds none whole."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register  # noqa: E402

WORDS = tuple(w.encode() for w in bug_register.PRIVATE_WORDS)     # one list, kept in pieces in the register tool
INSTRUCTION_FILES = frozenset(n.lower() for n in ('AGE' + 'NTS.md', 'GEM' + 'INI.md', '.cursor' + 'rules',
                                                  '.windsurf' + 'rules', '.cline' + 'rules',
                                                  'co' + 'pilot-instructions.md', 'cla' + 'ude.md'))


def public_files():
    listed = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
    try:
        tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, check=True)
        listed = sorted(set(listed) | {p for p in tracked.stdout.decode('utf-8').split('\0') if p})
    except (OSError, subprocess.CalledProcessError):
        pass                               # a source tree without git (a release ZIP): the public list alone
    return listed


def hits(path, data):
    lowered = data.lower()
    found = [w.decode() for w in WORDS if w in lowered]
    named = [w.decode() for w in WORDS if w in path.lower().encode()]
    return found, named


class PublicTreeWords(unittest.TestCase):
    def test_no_file_names_or_holds_a_private_word(self):
        bad = []
        for name in public_files():
            path = ROOT / name
            if not path.is_file():
                continue
            found, named = hits(name, path.read_bytes())
            if named:
                bad.append('%s: its path names %s' % (name, ', '.join(named)))
            if found:
                bad.append('%s: holds %s' % (name, ', '.join(found)))
        self.assertEqual(bad, [], 'private words in the public tree:\n' + '\n'.join(bad))

    def test_no_assistant_instruction_file(self):
        bad = [name for name in public_files() if Path(name).name.lower() in INSTRUCTION_FILES]
        self.assertEqual(bad, [], 'assistant instruction files in the public tree: ' + ', '.join(bad))

    def test_the_register_refuses_the_words(self):
        for word in WORDS:
            bug = {'id': 'X-1', 'title': 'a note naming ' + word.decode() + '/notes'}
            self.assertTrue([e for e in bug_register.validate_facts(bug, set(), set(), 'X-1') if 'private word' in e])
        self.assertEqual([e for e in bug_register.validate_facts({'id': 'X-2', 'title': 'clean'}, set(), set(), 'X-2')
                          if 'private word' in e], [])

    def test_the_check_finds_each_word(self):
        for word in WORDS:
            self.assertEqual(hits('docs/x.md', b'a ' + word.upper() + b' b')[0], [word.decode()])
            self.assertEqual(hits(word.decode() + '/notes.md', b'')[1], [word.decode()])


if __name__ == '__main__':
    unittest.main()
