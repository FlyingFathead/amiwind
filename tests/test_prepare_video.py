import shutil
import subprocess
import tempfile
import unittest
import json
import shlex
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
            self.assertEqual(result["audio_status"], "source_stream_converted")
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

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires ffmpeg and ffprobe")
    def test_silent_video_gets_exact_silent_pcm_without_losing_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "silent.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                            "testsrc2=size=320x180:rate=10", "-t", "0.4", "-c:v", "ffv1",
                            "-an", str(source)], check=True)
            result = prepare_video(source, root / "silent-out")
            self.assertEqual(result["audio_status"], "synthesized_silence")
            self.assertEqual(result["frames"], 4)
            self.assertEqual(result["seconds"], 0.4)
            self.assertEqual(result["samples"], 4410)
            payload = (root / "silent-out/mw_intro.awv").read_bytes()
            audio_start = 32 + 768 + result["frames"] * result["width"] * result["height"]
            self.assertEqual(payload[audio_start:], bytes(result["samples"]))
            self.assertEqual(validate(root / "silent-out/mw_intro.awv")["seconds"], 0.4)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires ffmpeg and ffprobe")
    def test_present_but_failing_audio_decode_is_not_replaced_with_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "audio.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-f", "lavfi", "-i",
                            "testsrc2=size=320x180:rate=10", "-f", "lavfi", "-i",
                            "sine=frequency=440:sample_rate=11025", "-t", "0.4", "-c:v",
                            "ffv1", "-c:a", "pcm_s16le", str(source)], check=True)
            wrapper = root / "ffmpeg-fail-audio.sh"
            wrapper.write_text('#!/bin/sh\nfor arg do\n  if [ "$arg" = "-vn" ]; then\n'
                               '    echo "injected audio decode failure" >&2\n    exit 41\n  fi\ndone\n'
                               'exec ' + shlex.quote(shutil.which("ffmpeg")) + ' "$@"\n', encoding="utf-8")
            wrapper.chmod(0o755)
            with self.assertRaises(subprocess.CalledProcessError) as error:
                prepare_video(source, root / "failed-out", ffmpeg=str(wrapper))
            self.assertEqual(error.exception.returncode, 41)

    def test_logo_hold_and_switchable_opening_card(self):
        from prepare_logo import prepare_logo, prepare_opening_card
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            Image.new('RGBA',(100,40),(255,255,255,255)).save(p/'logo.png')
            info=prepare_logo(p/'logo.png',p/'logo.awv')
            self.assertEqual(info['frames'],80)
            raw=(p/'logo.awv').read_bytes()
            frames=[raw[800+i*64000:800+(i+1)*64000] for i in range(80)]
            self.assertTrue(all(frame==frames[20] for frame in frames[20:70]))
            self.assertNotEqual(frames[19],frames[20])
            self.assertNotEqual(frames[70],frames[20])
            self.assertEqual(frames[0],frames[-1])
            font=p/'font.awf'
            font.write_bytes(struct.pack('<4sBBH',b'AWF1',16,18,1)+
                             struct.pack('<HBBbbBB',0,1,1,0,0,2,0)*256+b'\xc0')
            cards=p/'cards.json';cards.write_text(json.dumps([{'start':.5,'end':7,'text':'Opening'}]))
            info=prepare_opening_card(cards,font,p/'opening.awt',200)
            self.assertEqual((info['first_frame'],info['end_frame']),(5,70))
            self.assertEqual(len((p/'opening.awt').read_bytes()),64784)
            with self.assertRaises(ValueError):prepare_opening_card(cards,font,p/'invalid.awt',30)
