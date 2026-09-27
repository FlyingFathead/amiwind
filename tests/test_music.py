import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location("prepare_music", Path(__file__).resolve().parents[1] / "tools/prepare_music.py")
music = importlib.util.module_from_spec(spec)
spec.loader.exec_module(music)


class MusicTests(unittest.TestCase):
    def test_playlist_aliases_and_event_separation(self):
        names = [("Special/morrowind title.mp3", "title"), ("Explore/Morrowind Title.mp3", "title"),
                 ("Explore/a.mp3", "a"), ("Explore/b.mp3", "b"), ("Battle/c.mp3", "c"),
                 ("Special/mw_death.mp3", "death"), ("Special/mw_triumph.mp3", "win")]
        tracks = [{"source": "Music/" + name, "sha256": digest, "file": f"track{i:02}.mws"}
                  for i, (name, digest) in enumerate(names)]
        result = music.playlists(tracks)
        self.assertEqual(result["title"], 0)
        self.assertEqual(result["explore"], [2, 3])
        self.assertEqual(result["battle"], [4])
        self.assertEqual(result["special"], [0, 5, 6])
        include = music.music_include({"tracks": tracks}, {t["file"]: "MWBOOT:music/" + t["file"] for t in tracks})
        self.assertIn("music_explore:\n        dc.w 2,2,3", include)
        self.assertIn("music_battle:\n        dc.w 1,4", include)

    def test_no_battle_falls_back_and_no_explore_rejected(self):
        tracks = [{"source": "Music/Explore/x.mp3", "sha256": "x"}]
        result = music.playlists(tracks)
        self.assertEqual(result["battle"], result["explore"])
        self.assertEqual(result["title"], 0)
        with self.assertRaises(ValueError):
            music.playlists([{"source": "Music/Special/x.mp3", "sha256": "x"}])

    def test_channel_order_boundary_and_tail(self):
        # Distinct channels across a block boundary, including negative signed bytes.
        raw = bytes([17, 201]) * 8191 + bytes([33, 199, 44, 188, 55, 177])
        packed = music.pack_stream(raw)
        self.assertEqual(struct.unpack_from(">4sHHII", packed), (b"MWA1", 11015, 8192, 8194, 2))
        self.assertEqual(packed[16:20], bytes([201]) * 4)
        self.assertEqual(packed[16 + 8192:20 + 8192], bytes([17]) * 4)
        self.assertEqual(packed[16 + 16384:20 + 16384], bytes([188, 177, 0, 0]))
        self.assertEqual(music.unpack_stream(packed), raw)

    def test_title_alias_is_removed_from_both_world_groups(self):
        tracks = [{"source": name, "sha256": digest} for name, digest in
                  [("Music/Explore/title.mp3", "title"),
                   ("Music/Battle/copy.mp3", "title"),
                   ("Music/Special/morrowind title.mp3", "title"),
                   ("Music/Explore/real.mp3", "world"),
                   ("Music/Battle/real.mp3", "fight")]]
        result = music.playlists(tracks)
        self.assertEqual(result["explore"], [3])
        self.assertEqual(result["battle"], [4])
        with self.assertRaises(ValueError):
            music.playlists(tracks[:3])

    def test_rejects_broken_header_body_and_padding(self):
        good = music.pack_stream(bytes([1, 2]))
        for data in [b"", good[:-1], b"BAD!" + good[4:], good[:-1] + b"\1"]:
            with self.assertRaises(ValueError):
                music.unpack_stream(data)
        for pcm in [b"", b"\1"]:
            with self.assertRaises(ValueError):
                music.pack_stream(pcm)
