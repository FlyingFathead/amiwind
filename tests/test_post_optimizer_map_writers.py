# SPDX-License-Identifier: GPL-3.0-only
"""Maps written after the map optimizer keep its receipt true (CHIM-ROOM-FAST-MB-AFTER-OPTIMIZER-48).

dev2 try 13 stopped in the image step: the CHIM room heap gate marked 16 room maps "_chim_room_fast_mb" "32" after the
optimizer had recorded every staged map's hash, and the final optimizer check found them changed. The receipt now
follows exactly the marked maps (tools/optimize_world_maps.py rebind_marked_maps), and the image step checks the
receipt right before the marking, so any other change still stops the image. The early check: every call in the image
step that writes maps after the optimizer is followed by a receipt rebind before the next receipt reader (no silent
writers)."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chim import heap as H  # noqa: E402
from chim.frame_map import entities  # noqa: E402
from optimize_world_maps import optimize_maps, rebind_marked_maps, verify_optimized_maps  # noqa: E402
from test_chim_room_fast_ram import ROOM_32, ZONE_16, fake_heap, write_room  # noqa: E402
from test_share_bsp_geometry import repeated_geometry  # noqa: E402

MARK = '"%s" "%d"' % (H.ROOM_FAST_KEY, H.SAFE_FAST_MB)

# Calls in the image step (build_aga.py finalize_image) that write staged maps after the optimizer, and what binds
# the receipt to what they wrote. A new writer goes here with its rebind, or the test below fails.
WRITERS = ('chim_frame_maps(', 'require_room_map_heap(', 'mark_room_fast_ram(', 'mark_frame_maps(')
REBINDS = ('rebind_chim_maps(', 'rebind_marked_maps(')
READERS = ('verify_optimized_maps(', 'audit_world_map_heap_with_receipt(', 'bind_heap_report(',
           'image_content_fingerprint(')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RoomMarksKeepTheReceipt(unittest.TestCase):
    def staged(self, tmp):
        maps = Path(tmp) / 'maps'
        maps.mkdir()
        (maps / 'a.bsp').write_bytes(repeated_geometry())
        for name in ('small', 'big'):
            write_room(tmp, name)
        report = optimize_maps(maps, Path(tmp) / 'receipt.json')
        return maps, report

    def mark(self, tmp):
        needs = {'small': (3 << 20, 1 << 20), 'big': (ZONE_16 + (1 << 20), 2 << 20)}
        with mock.patch.object(H, 'room_map_heap', fake_heap(needs)):
            return H.require_room_map_heap(tmp, sizes={'hunk': 16})

    def test_marking_without_the_rebind_is_the_try13_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps, report = self.staged(tmp)
            self.assertEqual(self.mark(tmp)['marked_32mb'], ['big'])
            with self.assertRaisesRegex(ValueError, 'no longer match'):
                verify_optimized_maps(maps, report)

    def test_the_receipt_follows_exactly_the_marked_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps, report = self.staged(tmp)
            before = sha(maps / 'big.chim')
            verify_optimized_maps(maps, report)
            room = self.mark(tmp)
            report = rebind_marked_maps(maps, report, Path(tmp) / 'receipt.json',
                                        [room['rooms'][n]['map'] for n in room['marked_32mb']], MARK)
            verify_optimized_maps(maps, report)
            rows = {r['map']: r for r in report['maps']}
            self.assertEqual(entities((maps / 'big.chim').read_bytes())[0][H.ROOM_FAST_KEY], '32')
            self.assertEqual(rows['big.chim']['output_sha256'], sha(maps / 'big.chim'))
            self.assertEqual(rows['big.chim']['marked_from_sha256'], before)
            self.assertEqual(rows['big.chim']['marked'], MARK)
            self.assertNotIn('marked', rows['small.chim'])
            self.assertEqual(report['post_optimizer_marks'], [{'mark': MARK, 'maps': ['big.chim']}])
            self.assertEqual(json.loads((Path(tmp) / 'receipt.json').read_text())['post_optimizer_marks'],
                             report['post_optimizer_marks'])

    def test_any_other_change_still_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps, report = self.staged(tmp)
            self.mark(tmp)
            # another room map changed beside the mark: the rebind of the marked one does not hide it
            (maps / 'small.chim').write_bytes((maps / 'small.chim').read_bytes() + b'\0' * 4)
            with self.assertRaisesRegex(ValueError, 'no longer match'):
                rebind_marked_maps(maps, report, Path(tmp) / 'receipt.json', ['big.chim'], MARK)
        for names, error in ((['gone.chim'], 'not in the optimizer receipt'),
                             (['a.bsp'], 'optimizer optimized|not CHIM room maps')):
            with tempfile.TemporaryDirectory() as tmp:
                maps, report = self.staged(tmp)
                with self.assertRaisesRegex(ValueError, error):
                    rebind_marked_maps(maps, report, Path(tmp) / 'receipt.json', names, MARK)

    def test_marked_rooms_are_measured_again_as_they_ship(self):
        calls = []
        heap = fake_heap({'small': (3 << 20, 1 << 20), 'big': (ZONE_16 + (1 << 20), 2 << 20)})

        def counted(id1, sizes, heap_mb=None, stems=None):
            calls.append(None if stems is None else sorted(stems))
            return heap(id1, sizes, heap_mb, stems)
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('small', 'big'):
                write_room(tmp, name)
            with mock.patch.object(H, 'room_map_heap', counted):
                report = H.require_room_map_heap(tmp, sizes={'hunk': 16})
        self.assertEqual(calls, [None, ['big']])
        self.assertTrue(report['rooms']['big']['marked'])
        self.assertEqual(report['rooms']['big']['zone_32mb_bytes'], ROOM_32)


class NoSilentWriters(unittest.TestCase):
    def test_every_writer_after_the_optimizer_is_rebound(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        body = source[source.index('def finalize_image(args):'):]
        body = body[:re.search(r'\ndef ', body[1:]).start() + 1]
        body = body[body.index('optimize_maps(boot/'):]
        events = sorted((m.start(), name) for name in WRITERS + REBINDS + READERS
                        for m in re.finditer(r'(?<![\w.])' + re.escape(name), body))
        names = [name for _, name in events]
        self.assertIn('require_room_map_heap(', names)
        for i, name in enumerate(names):
            if name not in WRITERS:
                continue
            after = [n for n in names[i + 1:] if n not in WRITERS]
            self.assertTrue(after and after[0] in REBINDS, '%s is not followed by a receipt rebind: %s' % (name, after[:3]))
        # the room marking: the receipt is checked right before it, so only the marks change between check and rebind
        room = names.index('require_room_map_heap(')
        self.assertEqual(names[room - 1], 'verify_optimized_maps(')
        self.assertEqual(names[room + 1], 'rebind_marked_maps(')
        self.assertLess(room, names.index('audit_world_map_heap_with_receipt('))

    def test_the_room_mark_is_written_only_by_the_room_heap_gate(self):
        callers = []
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            text = path.read_text(encoding='utf-8', errors='replace')
            if re.search(r'(?<!def )\bmark_room_fast_ram\(', text):
                callers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(callers, ['tools/chim/heap.py'])
        heap = (ROOT / 'tools/chim/heap.py').read_text(encoding='utf-8')
        gate = heap[heap.index('def require_room_map_heap('):heap.index('def mark_room_fast_ram(')]
        self.assertIn('mark_room_fast_ram(', gate)
        self.assertEqual(len(re.findall(r'(?<!def )\bmark_room_fast_ram\(', heap)), 1)


if __name__ == '__main__':
    unittest.main()
