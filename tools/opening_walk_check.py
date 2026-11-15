# SPDX-License-Identifier: GPL-3.0-only
"""The opening walk's dock guard check (PIER-GUARD-WALKS-INTO-DOOR-65): reads a session's console log and asserts that
the dock guard reached his post beside the census office door.

aw_intro_status prints "Dock guard at X Y Z / leg L / route started S failed F done D / retries R" (aw_opening.c
AW_OpeningDockStatus). A walk passes only when a line with done 1 is seen within LIMIT status lines after the first
line of his second walk (leg 0 or 1 with the route started), and his place then is within RADIUS of the post.

    python3 tools/opening_walk_check.py LOG [--limit 12] [--radius 24]
exit 0 = reached, 1 = not reached (the last place and state printed), 2 = no dock guard line in the log.
"""
import argparse
import math
import re
import sys

POST = (286.0, -214.0)     # aw_opening.c AW_PIER_GUARD_POST_X / _Y
LINE = re.compile(r'Dock guard at (-?\d+) (-?\d+) (-?\d+) / leg (\d+) / route started (\d+) failed (\d+) done (\d+)'
                  r' / retries (\d+)')


def rows(text):
    return [tuple(int(v) for v in m.groups()) for m in LINE.finditer(text)]


def check(text, limit=12, radius=24.0):
    """(code, message) for a console log's text."""
    found = rows(text)
    if not found:
        return 2, 'no dock guard status line (aw_intro_status) in the log'
    start = next((i for i, r in enumerate(found) if r[4] or r[3]), None)
    if start is None:
        start = 0
    for i, r in enumerate(found[start:start + limit + 1]):
        if r[6]:
            d = math.hypot(r[0] - POST[0], r[1] - POST[1])
            if d <= radius:
                return 0, 'dock guard at his post %d %d after %d status lines (%.0f from the post)' % (r[0], r[1], i, d)
            return 1, 'dock guard done at %d %d, %.0f from the post' % (r[0], r[1], d)
    last = found[min(len(found), start + limit + 1) - 1]
    return 1, ('dock guard did not reach his post within %d status lines: last at %d %d, leg %d, failed %d, retries %d'
               % (limit, last[0], last[1], last[3], last[5], last[7]))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('log')
    p.add_argument('--limit', type=int, default=12)
    p.add_argument('--radius', type=float, default=24.0)
    a = p.parse_args(argv)
    with open(a.log, encoding='utf-8', errors='replace') as f:
        code, message = check(f.read(), a.limit, a.radius)
    print(('PASS ' if code == 0 else 'FAIL ') + message)
    return code


if __name__ == '__main__':
    sys.exit(main())
