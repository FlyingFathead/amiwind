import unittest

from build_aga import require_complete_media_outputs


CATEGORIES = ('videos', 'music', 'voices', 'effects')


def report(status='complete'):
    return {
        'status': status,
        'categories': {
            name: {'included': 0, 'missing_source': 0, 'missing_output': 0,
                   'available_sources': 0}
            for name in CATEGORIES
        },
    }


class MediaOutputGateTests(unittest.TestCase):
    def test_missing_original_sources_remain_warnings_not_a_fatal_gate(self):
        coverage = report()
        coverage['categories']['voices'].update(missing_source=9, available_sources=4)
        self.assertTrue(require_complete_media_outputs(coverage))

    def test_missing_converted_output_fails_with_category_and_count(self):
        coverage = report('missing_outputs')
        coverage['categories']['videos'].update(
            included=14, available_sources=17, missing_output=3)
        with self.assertRaisesRegex(
                ValueError, r'Available original media lacks validated converted output: videos=3'):
            require_complete_media_outputs(coverage)
        self.assertEqual(coverage['categories']['videos']['missing_output'], 3)

    def test_incomplete_status_without_missing_output_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'status is not complete'):
            require_complete_media_outputs(report('unknown'))

    def test_missing_category_fails_closed(self):
        coverage = report()
        del coverage['categories']['effects']
        with self.assertRaisesRegex(ValueError, 'missing counts for effects'):
            require_complete_media_outputs(coverage)

    def test_finalize_persists_coverage_then_gates_before_world_packing(self):
        from pathlib import Path
        import build_aga
        source = Path(build_aga.__file__).read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image(args):'):]
        report_write = finalize.index('media_coverage_path.write_text')
        gate = finalize.index('require_complete_media_outputs(media_coverage)')
        world_pack = finalize.index('pack_world_volumes(boot')
        self.assertLess(report_write, gate)
        self.assertLess(gate, world_pack)

    def test_invalid_missing_output_count_fails_closed(self):
        coverage = report()
        coverage['categories']['music']['missing_output'] = True
        with self.assertRaisesRegex(ValueError, 'invalid missing_output count for music'):
            require_complete_media_outputs(coverage)


if __name__ == '__main__':
    unittest.main()