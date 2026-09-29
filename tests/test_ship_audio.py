"""Convert synthetic source audio through the production host gain/loop path."""
import hashlib
import io
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_intro import ship_hull_convert, voice_convert

class Assets:
    def __init__(self):
        out = io.BytesIO()
        with wave.open(out, 'wb') as w:
            w.setparams((1, 2, 11025, 0, 'NONE', 'not compressed'))
            w.writeframes(b''.join(struct.pack('<h', round(24000*math.sin(i*.13))) for i in range(11025)))
        self.raw = out.getvalue()
    def read(self, name):
        return self.raw

def rms(path):
    with wave.open(str(path)) as w:
        assert w.getsampwidth() == 1
        raw = w.readframes(w.getnframes())
    return math.sqrt(sum((n-128)**2 for n in raw)/len(raw))

@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg required')
class ShipAudioTests(unittest.TestCase):
    def test_five_db_once_with_preserved_loop_and_source(self):
        assets = Assets()
        with tempfile.TemporaryDirectory() as tmp:
            full, quiet = (Path(tmp)/n for n in ('full.wav', 'quiet.wav'))
            voice_convert(assets, 'hull.wav', full, speech=False)
            report = ship_hull_convert(assets, 'hull.wav', quiet)
            original = quiet.read_bytes()
            self.assertAlmostEqual(20*math.log10(rms(quiet)/rms(full)), -5, delta=.05)
            self.assertEqual(report['gain_db'], -5)
            self.assertEqual(report['source_sha256'], hashlib.sha256(assets.raw).hexdigest())
            self.assertEqual(report['output_sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(original.count(b'cue '), 1)
            self.assertEqual(struct.unpack_from('<I', original, 4)[0]+8, len(original))
            ship_hull_convert(assets, 'hull.wav', quiet)
            self.assertEqual(quiet.read_bytes(), original)
            self.assertFalse(quiet.with_suffix('.lip').exists())
    def test_invalid_gain_rejected_before_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'bad.wav'
            for gain in (float('nan'), float('inf'), -61, 1):
                with self.assertRaises(ValueError):
                    voice_convert(Assets(), 'hull.wav', out, gain_db=gain)
            self.assertFalse(out.exists())
