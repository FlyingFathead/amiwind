import shutil
import subprocess
import tempfile
import unittest
import json
import struct
from pathlib import Path

from prepare_video import prepare_video, validate


class VideoTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "requires ffmpeg")
    def test_conversion_and_truncated_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "synthetic.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                            "testsrc2=size=320x180:rate=10", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=11025", "-t", "0.4", "-c:v",
                            "ffv1", "-c:a", "pcm_s16le", str(source)], check=True)
            result = prepare_video(source, root / "out")
            self.assertEqual(result["frames"], 4)
            self.assertEqual((result["width"], result["height"]), (320, 200))
            low = prepare_video(source, root / "low", size=(160, 100))
            self.assertEqual((low["width"], low["height"]), (160, 100))
            self.assertEqual(result["samples"], 4410)
            # A tiny thumbnail must not turn title-card gold into a movie color.
            font=root/'synthetic.awf'
            font.write_bytes(struct.pack('<4sBBH',b'AWF1',16,18,1)+
                             struct.pack('<HBBbbBB',0,1,1,0,0,2,0)*256+b'\xc0')
            captions=root/'cards.json';captions.write_text(json.dumps([{'start':0,'end':.4,'text':'ABC'}]))
            prepare_video(source,root/'cards',captions=captions,font=font)
            raw=(root/'cards/mw_intro.awv').read_bytes();pal=raw[32:800]
            colors={tuple(pal[i*3:i*3+3]) for i in raw[800:64800]}
            self.assertEqual(colors,{(0,0,0),(223,199,144)})
            path = root / "out/mw_intro.awv"
            self.assertEqual(validate(path)["frames"], 4)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "Truncated"):
                validate(path)
