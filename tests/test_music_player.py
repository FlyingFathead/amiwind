"""Compile the actual GPLv2 player against a synthetic host-side PCM oracle."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_music import pack_stream


@unittest.skipUnless(shutil.which("cc"), "host C compiler required")
class MusicPlayerTests(unittest.TestCase):
    def test_full_tracks_channels_tails_history_and_bad_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "quakedef.h").write_text('''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned char byte;typedef int qboolean;
#define MAX_OSPATH 1024
static char com_gamedir[1024];
static struct {float value;} bgmvolume={1.0};
static double Sys_FloatTime(void){return 0;}
static void Con_Printf(const char *fmt,...){(void)fmt;}
static void Cmd_AddCommand(const char *name,void(*fn)(void)){(void)name;(void)fn;}
''')
            (p / "sound.h").write_text("typedef struct {int left,right;} portable_samplepair_t;\n")
            # Keep the exact production code beside the synthetic headers so
            # its quoted includes do not select Amiga platform headers.
            shutil.copyfile(ROOT / "engine/aga/src/aw_music.c", p / "aw_music.c")
            exe = p / "player-test"
            subprocess.run(["cc", "-std=gnu89", "-O2", "-I" + str(p), "-I" + str(ROOT / "engine/aga/src"),
                            str(ROOT / "tests/music_player_test.c"), "-o", str(exe)], check=True)
            (p / "music").mkdir()
            for number, frames in zip((0, 11, 42, 83), (8200, 16413, 9001, 11)):
                pcm = bytes(v for i in range(frames) for v in ((i*3+number*17)%256, (i*7+number*31)%256))
                (p / "music" / f"track{number:02}.mws").write_bytes(pack_stream(pcm))
            playlist = p / "music/playlist.txt"
            playlist.write_text("3 0 11 42\n2 42 83\n")
            subprocess.run([str(exe), str(p), "normal"], cwd=p, check=True, timeout=10)
            events = (p / "music-events.csv").read_text().splitlines()
            completed = [line.split(",") for line in events[1:] if ",complete," in line]
            self.assertGreaterEqual(len(completed), 18)
            self.assertTrue(all(row[-1] == row[-2] for row in completed))
            playlist.write_text("1 0\n1 0\n")
            stream = p / "music/track00.mws"
            stream.write_bytes(stream.read_bytes()[:20])
            subprocess.run([str(exe), str(p), "truncated"], cwd=p, check=True, timeout=10)
            playlist.write_text("100 0\n1 0\n")
            subprocess.run([str(exe), str(p), "invalid"], cwd=p, check=True, timeout=10)
