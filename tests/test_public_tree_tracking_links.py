# SPDX-License-Identifier: GPL-3.0-only
"""No tracking query in any link of the public tree (the gate, every commit).

The maintainer, 29 October 2026: no public doc or link may ever carry a utm source query (his example named the
utm_source parameter after a question mark), "or any other", and "could be a release gate check for docs". A link copied from a search or a chat answer
often carries such a query (utm_source, utm_medium, fbclid, gclid and the like): it tells the linked site where the
reader came from and is never part of the address. Every file of the public list (tools/release-files.json) and every
file git tracks is checked; the parameter names are kept in pieces here so this file holds none whole."""
import re
import unittest
from pathlib import Path

from test_public_tree_private_words import ROOT, public_files

NAMES = ('ut' + 'm_[a-z]+', 'fb' + 'clid', 'gc' + 'lid', 'ms' + 'clkid', 'mc' + '_cid', 'mc' + '_eid', 'ig' + 'shid',
         'ref' + '_src', '_' + 'hsenc', 'yc' + 'lid')
TRACKING = re.compile(rb'[?&](?:' + '|'.join(NAMES).encode() + rb')=', re.IGNORECASE)
TEXT = {'.md', '.txt', '.html', '.htm', '.json', '.js', '.css', '.py', '.c', '.h', '.qc', '.cfg', '.yml', '.yaml',
        '.sh', '.toml', '.ini', '.xml', '.svg', ''}


def tracking_links(data):
    """Each line holding a tracking query, as (line number, the matched parameter)."""
    out = []
    for number, line in enumerate(data.splitlines(), 1):
        for match in TRACKING.finditer(line):
            out.append((number, match.group(0).decode('latin-1')))
    return out


class PublicTreeTrackingLinks(unittest.TestCase):
    def test_no_public_file_links_with_a_tracking_query(self):
        bad = []
        for name in public_files():
            path = ROOT / name
            if not path.is_file() or path.suffix.lower() not in TEXT:
                continue
            for number, found in tracking_links(path.read_bytes()):
                bad.append('%s:%d: %s' % (name, number, found))
        self.assertEqual(bad, [], 'tracking queries in public links (drop the ?... part): ' + '; '.join(bad[:20]))

    def test_the_check_finds_the_usual_forms(self):
        q = '?' + 'ut' + 'm_source=x'
        self.assertEqual(len(tracking_links(('[a](https://example.org/page%s)' % q).encode())), 1)
        self.assertEqual(len(tracking_links(('https://e.org/?id=3&' + 'fb' + 'clid=Z').encode())), 1)
        self.assertEqual(tracking_links(b'https://example.org/page?id=3&lang=en'), [])
        self.assertEqual(tracking_links(b'a variable named utm without a query'), [])


if __name__ == '__main__':
    unittest.main()
