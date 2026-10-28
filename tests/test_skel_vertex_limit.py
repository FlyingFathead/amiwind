"""SKEL-VERTEX-LIMIT-52: the skeletal model's vertex limit is the engine's, read from the source being built.

Up to v0.0.53 the alias stream reader, the only reader of a skeletal actor's block, refused any model past 2,000
vertices, while the renderer drew up to MAXALIASVERTS (engine/aga/src/r_local.h, 3,072: 1,024 triangles, per-model
opt-in through model-budgets.txt), so a skeletal actor with whole hair or a full-detail head could not be read. The
stream reader now takes extended models up to MAXALIASVERTS with the model's byte-matching model-budgets.txt line (a
CRC-32 computed while it reads), as the generic loader does. These checks keep the builder's limits equal to the
engine's."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
SRC = ROOT / 'engine' / 'aga' / 'src'


def define(path, name):
    m = re.search(r'^#define\s+%s\s+(\d+)' % name, (SRC / path).read_text(encoding='utf-8'), re.M)
    if not m:
        raise AssertionError('%s: no #define %s' % (path, name))
    return int(m.group(1))


class SkelVertexLimit(unittest.TestCase):
    def test_builder_limit_is_the_engines(self):
        import skeletal_actor
        self.assertEqual(skeletal_actor.SKEL_VERTEX_LIMIT, define('r_local.h', 'MAXALIASVERTS'))
        self.assertEqual(skeletal_actor.SKEL_FACE_LIMIT * 3, skeletal_actor.SKEL_VERTEX_LIMIT)
        # the readers of the built residents take the same limit (the actor-ground check failed a Balmora build)
        text = (ROOT / 'tools' / 'check_actor_ground.py').read_text(encoding='utf-8')
        self.assertIn('ACTOR_VERTEX_LIMIT=%d' % skeletal_actor.SKEL_VERTEX_LIMIT, text)
        self.assertNotIn('nv<=1999', text)
        import alias_stream_heap
        self.assertEqual(alias_stream_heap.STREAM_VERTEX_LIMIT, skeletal_actor.SKEL_VERTEX_LIMIT)

    def test_stream_reader_takes_extended_models_with_their_allowance(self):
        text = (SRC / 'model_alias_stream.inc').read_text(encoding='utf-8')
        self.assertNotRegex(text, r'nv\s*>\s*2000', 'the stream reader still refuses past 2,000 vertices')
        self.assertIn('nv>MAXALIASVERTS', text)
        self.assertIn('AW_AliasExceptionMatches', text)     # the byte-matching model-budgets.txt line
        self.assertEqual(define('quakedef.h', 'AW_ALIAS_NORMAL_VERTS'), 2000)

    def test_whole_hair_fits_the_skin_and_the_reader(self):
        import npc_geometry
        import skeletal_actor
        self.assertIn(skeletal_actor.SKEL_FACE_LIMIT, npc_geometry.ALIAS_FACE_LIMITS)
        self.assertLessEqual(npc_geometry.WHOLE_FACE_LIMIT * 3, skeletal_actor.SKEL_VERTEX_LIMIT)
        self.assertLessEqual(npc_geometry.WHOLE_FACE_LIMIT, skeletal_actor.SKEL_FACE_LIMIT)

    def test_crc_matches_the_image_steps(self):
        """The engine's CRC-32 (model.c AW_AliasCrcAdd: reflected 0xedb88320, start and end inverted) is zlib's, which
        the image step writes into model-budgets.txt (audit_gallery_budgets.world_allowances)."""
        import zlib
        text = (SRC / 'model.c').read_text(encoding='utf-8')
        self.assertIn('0xedb88320U', text)
        data = bytes(range(256)) * 3
        crc = 0xffffffff
        for b in data:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ (0xedb88320 & -(crc & 1))
        self.assertEqual(crc ^ 0xffffffff, zlib.crc32(data))


if __name__ == '__main__':
    unittest.main()
