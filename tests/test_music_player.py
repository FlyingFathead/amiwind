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
#include <strings.h>
typedef unsigned char byte;typedef int qboolean;
/* the combat music switch (AW_MusicDeath) looks tracks up by name */
static int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
#define MAX_OSPATH 1024
static char com_gamedir[1024];
static struct {float value;} bgmvolume={1.0};
static double test_now;
static double Sys_FloatTime(void){return test_now;}
static double realtime;
static int debug_overlay,track_notices,status_queries,stall_notices;
static int AW_DebugOverlaysEnabled(void){return debug_overlay;}
static void Con_Printf(const char *fmt,...){
    if(strstr(fmt,"OST %s: track"))track_notices++;
    if(strstr(fmt,"OST group="))status_queries++;
    if(strstr(fmt,"music read stalled"))stall_notices++;
}
static void Cmd_AddCommand(const char *name,void(*fn)(void)){(void)name;(void)fn;}
typedef struct cvar_s {char *name;char *string;qboolean archive;qboolean server;float value;struct cvar_s *next;} cvar_t;
static cvar_t *test_cvars;
static int Cmd_Argc(void){return 1;}
static char *Cmd_Argv(int i){(void)i;return "";}
static void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);v->next=test_cvars;test_cvars=v;}
static void Cvar_SetValue(char *name,float value){cvar_t *v;for(v=test_cvars;v;v=v->next)if(!strcmp(v->name,name))v->value=value;}
''')
            (p / "sound.h").write_text("typedef struct {int left,right;} portable_samplepair_t;\n")
            # Keep the exact production code beside the synthetic headers so
            # its quoted includes do not select Amiga platform headers.
            shutil.copyfile(ROOT / "engine/aga/src/aw_music.c", p / "aw_music.c")
            exe = p / "player-test"
            subprocess.run(["cc", "-std=gnu89", "-O2", "-I" + str(p), "-I" + str(ROOT / "engine/aga/src"),
                            str(ROOT / "tests/music_player_test.c"), str(ROOT / "engine/aga/src/aw_format.c"),
                            str(ROOT / "engine/aga/src/aw_log.c"), str(ROOT / "engine/aga/src/aw_aread.c"),
                            "-o", str(exe)], check=True)
            (p / "music").mkdir()
            for number, frames in zip((0, 4, 11, 42, 83), (8200, 9131, 16413, 9001, 11)):
                pcm = bytes(v for i in range(frames) for v in ((i*3+number*17)%256, (i*7+number*31)%256))
                (p / "music" / f"track{number:02}.mws").write_bytes(pack_stream(pcm))
            playlist = p / "music/playlist.txt"
            playlist.write_text("4 0 4 11 42\n2 42 83\n")
            long_pcm = bytes(v for i in range(41000) for v in ((i*3+11*17)%256, (i*7+11*31)%256))
            (p / "music/track11.mws").write_bytes(pack_stream(long_pcm))
            subprocess.run([str(exe), str(p), "buffered"], cwd=p, check=True, timeout=10)
            subprocess.run([str(exe), str(p), "notifications"], cwd=p, check=True, timeout=10)
            # HANG-IDLE-DUSK-35: a read that is late or never answered never stops the game loop.
            for case in ("stall-late", "stall-never"):
                subprocess.run([str(exe), str(p), case], cwd=p, check=True, timeout=10)
                events = (p / "music-events.csv").read_text().splitlines()
                self.assertEqual(sum(",read-stalled," in line for line in events),
                                 1 if case == "stall-late" else 3, case)
                if case == "stall-late":
                    self.assertTrue(any(",read-recovered," in line for line in events))
                    self.assertFalse(any(",read-abandoned," in line for line in events))
                else:
                    self.assertEqual(sum(",read-abandoned," in line for line in events), 3)
                    self.assertTrue(any(",stall-off," in line for line in events))
                    self.assertTrue(any(",stall-recovered," in line for line in events))
            # ENGINE-MUSIC-NO-OFF-SWITCH-36: dbg music off/on with a read outstanding.
            subprocess.run([str(exe), str(p), "switch"], cwd=p, check=True, timeout=10)
            events = (p / "music-events.csv").read_text().splitlines()
            self.assertEqual(sum(",music-off," in line for line in events), 1)
            self.assertEqual(sum(",music-on," in line for line in events), 1)
            subprocess.run([str(exe), str(p), "normal"], cwd=p, check=True, timeout=10)
            events = (p / "music-events.csv").read_text().splitlines()
            completed = [line.split(",") for line in events[1:] if ",complete," in line]
            self.assertGreaterEqual(len(completed), 18)
            self.assertTrue(all(row[-1] == row[-2] for row in completed))
            subprocess.run([str(exe), str(p), "demo"], cwd=p, check=True, timeout=10)
            events = (p / "music-events.csv").read_text().splitlines()
            demo = [line.split(',') for line in events if ',early_game_demo_start_1,' in line]
            self.assertTrue(demo)
            self.assertTrue(all(row[2:5] == ['0', '4', 'track04.mws'] for row in demo))
            playlist.write_text("4 0 4 11 42\n2 42 83\n83\n")
            subprocess.run([str(exe), str(p), "menu"], cwd=p, check=True, timeout=10)
            (p / 'music/track04.mws').unlink()
            subprocess.run([str(exe), str(p), "demo-missing"], cwd=p, check=True, timeout=10)
            playlist.write_text("1 0\n1 0\n")
            stream = p / "music/track00.mws"
            stream.write_bytes(stream.read_bytes()[:20])
            subprocess.run([str(exe), str(p), "truncated"], cwd=p, check=True, timeout=10)
            playlist.write_text("100 0\n1 0\n")
            subprocess.run([str(exe), str(p), "invalid"], cwd=p, check=True, timeout=10)
