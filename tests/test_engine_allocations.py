# SPDX-License-Identifier: GPL-2.0-or-later
"""Every engine allocation can fail without a Software Failure (SDK-MALLOC-TRAPS-52).

The Amiga toolchain's malloc never returns NULL: when exec has no block for a request its allocator (libc malloc.o,
MemMap::alloc) stores through the NULL AllocMem gave it and stops on TRAP #7 (Software Failure #80000027; found as
SKEL-16MB-TRAP-52). The engine therefore allocates through aw_tryalloc.h (AW_TryMalloc, AW_TryCalloc,
AW_TryRealloc), which asks exec's largest free block first and returns NULL as the callers expect. No engine source
calls malloc, calloc or realloc itself; aw_tryalloc.c is the one file that does."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
# the files that may call the C library's allocators themselves, each with its reason
ALLOWED = {
    'aw_tryalloc.c': 'the checked allocators themselves',
    'aw_tryalloc.h': 'the host builds\' macros: the C library\'s own, which return NULL there',
}
CALL = re.compile(r'\b(malloc|calloc|realloc|strdup)\s*\(')
COMMENT = re.compile(r'/\*.*?\*/|//[^\n]*', re.S)
STRING = re.compile(r'"(?:\\.|[^"\\\n])*"')


def sources():
    for path in sorted(SRC.rglob('*')):
        if path.suffix in ('.c', '.h', '.inc') and path.is_file():
            yield path


def calls(text):
    """(line, function) of every direct allocator call outside comments and string literals."""
    out = []
    code = STRING.sub('""', COMMENT.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text))
    for m in CALL.finditer(code):
        out.append((code.count('\n', 0, m.start()) + 1, m.group(1)))
    return out


class EngineAllocationTests(unittest.TestCase):
    def test_no_engine_source_calls_the_c_library_allocators(self):
        found = []
        for path in sources():
            rel = path.relative_to(SRC).as_posix()
            if rel in ALLOWED:
                continue
            found += ['%s:%d %s' % (rel, line, name) for line, name in calls(path.read_text(encoding='latin-1'))]
        self.assertEqual(found, [], 'use AW_TryMalloc / AW_TryCalloc / AW_TryRealloc (aw_tryalloc.h)')

    def test_the_scan_sees_a_call_and_not_a_comment(self):
        self.assertEqual(calls('p=malloc(4); /* malloc(8) */ q = calloc (1, 2); // realloc(p, 9)\n'
                               'r=AW_TryMalloc(3); s="malloc(1)"; t = realloc(p, 2);'),
                         [(1, 'malloc'), (1, 'calloc'), (2, 'realloc')])

    def test_the_checked_allocators_and_their_rule(self):
        header = (SRC / 'aw_tryalloc.h').read_text(encoding='utf-8')
        body = (SRC / 'aw_tryalloc.c').read_text(encoding='utf-8')
        for name in ('AW_TryMalloc', 'AW_TryCalloc', 'AW_TryRealloc'):
            self.assertIn('void *%s (' % name, header)
            self.assertIn('void *%s (' % name, body)
        self.assertIn('return (size > AW_TRYALLOC_POOL ? size + 4 : AW_TRYALLOC_BLOCK) + AW_TRYALLOC_SPARE;', body)
        self.assertIn('return (unsigned long)AvailMem (MEMF_LARGEST) >= AW_TryAllocNeed (size);', body)
        self.assertIn('if (size && total / size != count)', body)     # calloc's count x size overflow refused
        self.assertIn('#define AW_TryMalloc(size)\tmalloc (size)', header)  # host builds: the C library's own
        makefile = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_skel_load.c aw_skel_release.c aw_fastrelease.c aw_tryalloc.c', makefile)

    def test_a_refused_skeletal_table_is_said_once_per_model(self):
        stream = (SRC / 'model_alias_stream.inc').read_text(encoding='utf-8')
        self.assertIn('static const model_t *told[64];static int told_count;', stream)
        self.assertIn('if(!seen){', stream)


if __name__ == '__main__':
    unittest.main()
