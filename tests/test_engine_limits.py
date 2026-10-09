"""The builder's entity checks read the engine's own budgets (tools/engine_limits.py), never a copy.

A static entity limit written into a tool as a number drifts from the engine the day the engine's
define changes (client.h MAX_STATIC_ENTITIES), and the build then refuses or ships the wrong count.
The engine states the same names in the CHIM "chim" command (tests/aga_chim_world_test.c)."""
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import engine_limits  # noqa: E402


class EngineLimitTests(unittest.TestCase):
    def setUp(self):
        self.limits = engine_limits.limits()

    def test_limits_are_the_engine_defines(self):
        client = (ROOT / 'engine/aga/src/client.h').read_text()
        quakedef = (ROOT / 'engine/aga/src/quakedef.h').read_text()
        self.assertEqual(self.limits['max_static_entities'],
                         int(re.search(r'#define\s+MAX_STATIC_ENTITIES\s+(\d+)', client).group(1)))
        self.assertEqual(self.limits['max_edicts'], int(re.search(r'#define\s+MAX_EDICTS\s+(\d+)', quakedef).group(1)))
        self.assertEqual(self.limits['max_msglen'], int(re.search(r'#define\s+MAX_MSGLEN\s+(\d+)', quakedef).group(1)))
        self.assertIn('#define\t\t\tMAX_VISEDICTS\t(MAX_EDICTS + MAX_STATIC_ENTITIES)', client)
        self.assertEqual(self.limits['max_visedicts'], self.limits['max_edicts'] + self.limits['max_static_entities'])

    def test_every_builder_check_reads_the_same_static_limit(self):
        import prepare_world_flora
        import sprite_heap
        import world_estimate
        n = self.limits['max_static_entities']
        policy = sprite_heap.efrag_pool_profile((ROOT / 'engine/aga/src/client.h').read_text())
        self.assertEqual(policy['max_statics'], n)
        self.assertEqual(world_estimate.engine_limits()['max_static_entities'], n)
        self.assertEqual(prepare_world_flora.RESERVES['static_entities'], n - 32)
        # The sprite static count check refuses exactly one past the engine's limit.
        def statics(count):
            return b''.join(b'{\n"classname" "aw_static"\n"model" "progs/s.spr"\n"origin" "0 0 0"\n}\n'
                            for _ in range(count))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Static sprite entity limit exceeded'):
                sprite_heap.inspect_sprites(statics(n + 1), Path(tmp), {})
            try:
                sprite_heap.inspect_sprites(statics(n), Path(tmp), {})
            except (ValueError, KeyError, OSError) as exc:
                self.assertNotIn('limit exceeded', str(exc))

    def test_no_tool_keeps_its_own_copy_of_the_static_limit(self):
        n = self.limits['max_static_entities']
        pattern = re.compile(r'(static|statics|instances)[^\n]{0,40}[<>]=?\s*(%d|%d)\b' % (n, n - 32))
        found = []
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
                if pattern.search(line):
                    found.append('%s:%d: %s' % (path.relative_to(ROOT), number, line.strip()))
        self.assertEqual(found, [])

    def test_chim_memory_defaults_are_the_measured_ones(self):
        # v0.0.33-dev1: Balmora's CHIM frame map peaks at 9,218,800 Hunk bytes with a 6,656 KiB zone
        # (11 MiB Hunk); the zone may grow until the 2 MiB Hunk-gap safety, rounded down to 16 KiB.
        memory = engine_limits.chim_memory()
        hunk = memory['heap_mb'] * 1024 * 1024
        peak = 9218800 + (memory['zone_kib'] - 6656) * 1024
        self.assertGreaterEqual(hunk - peak, 2 * 1024 * 1024)
        self.assertLess(hunk - peak - 16 * 1024, 2 * 1024 * 1024)
        self.assertEqual(memory['zone_kib'] % 16, 0)
        self.assertEqual((memory['zone_kib'], memory['pool_kib'], memory['chunk_room_kib']), (6864, 384, 6096))
        doc = (ROOT / 'docs/chim/ENGINE.md').read_text()
        self.assertIn('default 6,864 KiB', doc)
        self.assertIn('default 384, so 768', doc)

    def test_the_whole_map_rule_gives_the_measured_largest_zones(self):
        # FS-UAE, 9 October 2026 (CHIM-SEYDA-HUNK-GAP-33): apart from the zone, Balmora's CHIM map holds
        # 2,403,104 Hunk bytes at its load peak (793,504 of them before the zone), Seyda Neen's 3,406,144
        # (825,744 before the zone).
        memory = engine_limits.chim_memory()
        self.assertEqual(memory['hunk_bytes'], 11 * 1024 * 1024)
        self.assertEqual(memory['gap_bytes'], 2 * 1024 * 1024)
        balmora = engine_limits.whole_map_zone(793504, 2403104 - 793504, memory)
        seyda = engine_limits.whole_map_zone(825744, 3406144 - 825744, memory)
        self.assertEqual(balmora // 1024, 6864)
        self.assertEqual(seyda // 1024, 5888)
        # A larger Hunk (the build's own heap size) moves the zone with it.
        bigger = engine_limits.chim_memory(heap_mb=12)
        self.assertEqual(engine_limits.whole_map_zone(825744, 3406144 - 825744, bigger) // 1024, 5888 + 1024)
        self.assertEqual(engine_limits.whole_map_zone(10 * 1024 * 1024, 2 * 1024 * 1024, memory), 0)

    def test_the_engine_keeps_the_whole_map_rule(self):
        text = (ROOT / 'engine/aga/src/chim/chim_world.c').read_text()
        self.assertIn('"_chim_hunk_rest"', text)
        self.assertIn('- rest_used - %d;' % engine_limits.ZONE_HEADER_BYTES, text)

    def test_the_engine_states_the_same_names(self):
        text = (ROOT / 'engine/aga/src/chim/chim_world.c').read_text()
        for name in ('MAX_STATIC_ENTITIES', 'MAX_EDICTS', 'MAX_VISEDICTS', 'MAX_MSGLEN', 'AW_EFRAG_LIMIT'):
            self.assertIn('(%s)' % name, text)


if __name__ == '__main__':
    unittest.main()
