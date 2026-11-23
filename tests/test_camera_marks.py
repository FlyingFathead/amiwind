# SPDX-License-Identifier: GPL-3.0-only
"""Named camera marks: dbg cam mark / recall / list (docs/CAMERA_MARKS.md, docs/history/plans/PLAN-v0.0.42.md 1.2c).

The public marks file (config/camera-marks.txt) holds the ten emulator benchmark cameras exactly as
docs/HARDWARE-BENCHMARK.md gives them and the Palace of Vivec comparison pose; the builder copies it onto the boot
disk; the engine's reader (aw_cam_rules.c) and tools/camera_marks.py accept and refuse the same lines; the
commands live under `dbg cam` (Mark and Recall are spells of the game) as one registered command."""
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import camera_marks  # noqa: E402
import console_commands_doc as doc  # noqa: E402


class PublicMarks(unittest.TestCase):
    def test_the_public_file_is_valid(self):
        marks = camera_marks.load()
        names = [m['name'] for m in marks]
        for name in ['bm%d' % i for i in range(1, 6)] + ['sn%d' % i for i in range(1, 6)] + ['vivec-palace']:
            self.assertIn(name, names)
        raw = camera_marks.PUBLIC.read_bytes()
        self.assertLessEqual(len(raw), camera_marks.FILE_LIMIT)
        self.assertTrue(raw.endswith(b'\n'))

    def test_benchmark_cameras_are_the_documented_ones(self):
        """Each Balmora / Seyda Neen camera of the benchmark table is a mark: dbg tp X Y, then aw_aim YAW PITCH,
        with the documented setup (day/night cycle off, time 1200, headlamp off) and the default fog distance."""
        table = (ROOT / 'docs' / 'HARDWARE-BENCHMARK.md').read_text(encoding='utf-8')
        rows = re.findall(r'^\| (Balmora|Seyda Neen) (\d) \| `dbg tp (-?\d+) (-?\d+)`, then `aw_aim (\d+) (-?\d+)` \|$',
                          table, re.M)
        self.assertEqual(len(rows), 10)
        marks = {m['name']: m for m in camera_marks.load()}
        for town, number, x, y, yaw, pitch in rows:
            mark = marks[('bm' if town == 'Balmora' else 'sn') + number]
            self.assertEqual(mark['place'], 'global')
            self.assertEqual(mark['point'], [float(x), float(y)])
            self.assertEqual((mark['yaw'], mark['pitch']), (float(yaw), float(pitch)))
            self.assertEqual((mark['time'], mark['headlamp'], mark['fog']), ('1200', False, 540))

    def test_the_palace_of_vivec_pose(self):
        mark = {m['name']: m for m in camera_marks.load()}['vivec-palace']
        self.assertEqual((mark['place'], mark['point'], mark['yaw'], mark['pitch']), ('vpi015', [0, -64.7, -83.9], 90, 0))
        self.assertIn('`vpi015`', (ROOT / 'docs' / 'MINIWIND.md').read_text(encoding='utf-8'))


class Format(unittest.TestCase):
    def check(self, line):
        return camera_marks.parse_line(line)

    def test_fields(self):
        m = self.check('bm1|global|-20088 -14638|113 -3|1200|off|540|Balmora 1')
        self.assertEqual((m['place'], m['point'], m['yaw'], m['pitch'], m['time'], m['headlamp'], m['fog']),
                         ('global', [-20088, -14638], 113, -3, '1200', False, 540))
        m = self.check('tz|global|1 2 300|0 0|-|-|-|')
        self.assertEqual((m['point'], m['time'], m['headlamp'], m['fog'], m['note']), ([1, 2, 300], None, None, None, ''))
        self.assertIsNone(self.check('# comment'))
        self.assertIsNone(self.check(''))

    def test_refused_lines_name_the_field(self):
        cases = {
            'bm1|global|-20088|113 -3|1200|off|540|': 'position',
            'm|vpi015|1 2|0 0|1200|off|540|': 'position',
            'm|VPI015|1 2 3|0 0|1200|off|540|': 'place',
            'm|vpi015|1 2 40000|0 0|1200|off|540|': 'position',
            'm|global|1  2|0 0|1200|off|540|': 'position',
            'm|global|1 2e3|0 0|1200|off|540|': 'position',
            'm|global|1 2|360 0|1200|off|540|': 'view',
            'm|global|1 2|0 81|1200|off|540|': 'view',
            'm|global|1 2|0 0|2400|off|540|': 'time',
            'm|global|1 2|0 0|1200|maybe|540|': 'headlamp',
            'm|global|1 2|0 0|1200|off|99|': 'fog',
            'm|global|1 2|0 0|1200|off|540': 'fields',
            'bad name|global|1 2|0 0|1200|off|540|': 'name',
        }
        for line, field in cases.items():
            with self.subTest(line=line):
                with self.assertRaisesRegex(camera_marks.MarkError, field):
                    self.check(line)

    def test_file_header_duplicates_and_limits(self):
        with self.assertRaisesRegex(camera_marks.MarkError, 'AWCM1'):
            camera_marks.parse(b'AWCM0\n')
        with self.assertRaisesRegex(camera_marks.MarkError, 'again'):
            camera_marks.parse(b'AWCM1\na|global|1 2|0 0|-|-|-|\nA|global|1 2|0 0|-|-|-|\n')
        with self.assertRaisesRegex(camera_marks.MarkError, 'CR'):
            camera_marks.parse(b'AWCM1\r\n')
        with self.assertRaisesRegex(camera_marks.MarkError, 'bytes'):
            camera_marks.parse(b'AWCM1\n' + b'#' * camera_marks.FILE_LIMIT)

    def test_cli(self):
        self.assertEqual(camera_marks.main(['check']), 0)
        with patch('sys.stdout'):
            self.assertEqual(camera_marks.main(['show', 'BM3']), 0)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EngineReader(unittest.TestCase):
    def test_the_engine_reads_and_writes_the_same_lines(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_cam_test.c', [SRC / 'aw_cam_rules.c'],
                                               arguments=[str(camera_marks.PUBLIC)])


class Command(unittest.TestCase):
    def test_one_command_under_dbg_cam(self):
        rows = doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))
        cam = [(words, handler) for _, words, handler, _ in rows if handler == 'aw_cam']
        # one command; the camera shots' own lines and the pan's alias route onto it (DBG-CAM-PAN-TRACK-68)
        self.assertEqual(cam, [('cam', 'aw_cam'), ('cam pan', 'aw_cam'), ('cam track', 'aw_cam'), ('pan cam', 'aw_cam')])
        # Mark and Recall are spells of the game: never a bare dbg mark / dbg recall
        self.assertFalse([w for _, w, _, _ in rows if w.split()[0] in ('mark', 'recall', 'marks')])
        engine = ''.join(f.read_text(encoding='latin-1') for f in sorted(SRC.rglob('*.c')))
        self.assertEqual(engine.count('Cmd_AddCommand("aw_cam"'), 1)
        self.assertIn('Cmd_AddCommand("aw_cam",cam_command);', (SRC / 'aw_cam.c').read_text(encoding='utf-8'))
        self.assertIn('AW_CamInit();', (SRC / 'aw_debug.c').read_text(encoding='utf-8'))
        self.assertIn('aw_debug.c aw_cam_rules.c aw_cam.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        self.assertIn('`dbg cam`', (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8'))

    def test_recall_travels_as_dbg_tp_and_touches_nothing_else(self):
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        shot = scene[scene.index('int AW_SceneShot('):scene.index('/* Ray/slab intersection')]
        self.assertIn('AW_MapTeleportAt(point,has_z)', shot)        # the dbg tp X Y [Z] route itself
        self.assertIn('SV_LinkEdict(p,false)', shot)                # a placement on this map touches no trigger
        self.assertNotIn('SV_LinkEdict(p,true)', shot)
        self.assertIn('load_scene(&r,1)', shot)                     # another map: the debug teleport's map load
        self.assertIn('if(map_jump==3){', scene)
        cam = (SRC / 'aw_cam.c').read_text(encoding='utf-8')
        recall = cam[cam.index('static int recall_command'):cam.index('static int make_folder')]
        # the benchmark order: clock held, time, headlamp, fog, then the travel
        order = [recall.index(s) for s in ('Cvar_SetValue("aw_daynightcycle",0)', 'aw_set_time %04d',
                                           'Cvar_SetValue("aw_headlamp"', 'AW_SetDrawDistance(m.fog)', 'AW_SceneShot(')]
        self.assertEqual(order, sorted(order))
        # a private mark never shadows a public one
        mark = cam[cam.index('static void mark_command'):cam.index('static void cam_command')]
        self.assertIn('is a public camera mark', mark)


class ViewInSolid(unittest.TestCase):
    """aw_view warns when its camera point is in solid or outside the room (SESSION-AW-VIEW-IN-SOLID-54)."""

    def test_aw_view_checks_the_eye_point_after_placing_it(self):
        debug = re.sub(r'/\*.*?\*/', '', (SRC / 'aw_debug.c').read_text(encoding='utf-8'), flags=re.S)
        view = debug[debug.index('static void view(void)'):debug.index('static void tcl(void)')]
        self.assertLess(view.index('SV_LinkEdict(p,false)'), view.index('view_check(p);'))
        check = debug[debug.index('static void view_check(edict_t *p)'):debug.index('static void view(void)')]
        self.assertIn('VectorAdd(p->v.origin,p->v.view_ofs,eye)', check)      # the eye, not the hull origin
        self.assertIn('tr.startsolid || tr.allsolid', check)                 # in solid
        self.assertIn('if(!AW_Interior())return;', check)                    # outside: interiors only
        self.assertEqual(check.count('SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p)'), 2)
        self.assertIn('tr.fraction>=1', check)
        # one fixed prefix the session tooling looks for in its console log
        self.assertEqual(check.count('"aw_view WARNING: '), 2)


class Orbit(unittest.TestCase):
    """dbg cam orbit: the vanity camera's placement around another centre, the player detached while it runs."""
    def setUp(self):
        self.view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        # the detachment the orbit and the shots share (camera_detach), and the orbit's start
        self.start = self.view[self.view.index('static void camera_detach(edict_t *p) {'):
                               self.view.index('/* ---- dbg cam pan and dbg cam track')]
        self.end = self.view[self.view.index('void AW_ViewOrbitEnd('):self.view.index('/* dbg cam orbit mark NAME')]

    def test_detached_while_it_runs_and_restored_after(self):
        for text in ('p->v.movetype=MOVETYPE_NOCLIP;', 'FL_GODMODE|FL_NOTARGET', 'SV_LinkEdict(p,false);', 'camera_detach(p);'):
            self.assertIn(text, self.start)
        self.assertNotIn('SV_LinkEdict(p,true)', self.start + self.end)
        for text in ('VectorCopy(orbit.origin,p->v.origin);', 'p->v.movetype=orbit.movetype;', 'p->v.flags=orbit.flags;',
                     'VectorCopy(orbit.view,cl.viewangles);', 'noclip_anglehack=orbit.anglehack;'):
            self.assertIn(text, self.end)
        # the player's body is not drawn (a shot started in third person keeps it), every game key goes to the orbit,
        # Esc / right click end it
        self.assertIn('|| (orbit.active && !orbit.body))return NULL;', self.view)
        self.assertIn('orbit.kind=AW_VIEW_CAM_ORBIT;orbit.body=0;', self.start)
        key = self.view[self.view.index('static int orbit_key('):self.view.index('static int orbit_camera(')]
        self.assertIn('return 1;                                                  /* every other game key: nothing */', key)
        self.assertIn('key==K_ESCAPE || key==K_MOUSE2', key)
        self.assertIn('if(orbit_key(key))return 1;', self.view)
        # a new map ends it
        spawn = self.view[self.view.index('void AW_ViewSceneSpawn(void) {'):]
        self.assertIn('if(orbit.active){', spawn[:400])

    def test_the_vanity_camera_placement_is_reused(self):
        camera = self.view[self.view.index('static int orbit_camera('):self.view.index('int AW_ViewCamera(void) {')]
        self.assertIn('trace(focal,end,hit,&fraction);', camera)
        self.assertIn('AW_ViewObstacle(orbit.distance,fraction,rules.obstacle)', camera)
        self.assertIn('if(orbit.active)return orbit_camera();', self.view)
        self.assertIn('if(owned && orbit.active)return orbit.photo;', self.view)      # photo: the vanity full view

    def test_notarget_reaches_the_ai(self):
        combat = (SRC / 'aw_combat.c').read_text(encoding='utf-8')
        think = combat[combat.index('static void think(slot_t *s,edict_t *p,float dt) {'):]
        # COMBAT-ACTOR-VS-ACTOR-62: notarget holds the slots whose target is the player (target_num 0)
        self.assertIn('if(!s->target_num && ((int)p->v.flags&FL_NOTARGET)){if(s->group!=G_IDLE)set_state(s,S_CHASE,G_IDLE);return;}', think[:4000])
        self.assertIn("if(!you.dead && !((int)p->v.flags&FL_NOTARGET))npc_strike(s,p);", combat)
        bark = (SRC / 'pr_cmds.c').read_text(encoding='utf-8')
        bark = bark[bark.index('static void PF_aw_bark(void)'):bark.index('builtin_t pr_builtin[]')]
        self.assertIn('FL_NOTARGET', bark)
        # greetings already need a walking player (world.qc aw_npc_idle: movetype 3); noclip is 8
        self.assertIn('aw_player.movetype != 3', (ROOT / 'engine' / 'aga' / 'qc' / 'world.qc').read_text(encoding='utf-8'))

    def test_the_command(self):
        cam = (SRC / 'aw_cam.c').read_text(encoding='utf-8')
        orbit = cam[cam.index('static void orbit_command(int argc)'):cam.index('static void cam_command(void)')]
        for word in ('"photo"', '"off"', '"speed"', '"ref"', '"mark"'):
            self.assertIn(word, orbit)
        self.assertIn('AW_InspectTarget(&number,focal)', orbit)        # the crosshair pick of dbg ent
        self.assertIn('AW_ViewOrbitPending(photo,rate)', orbit)        # mark: after the recall has arrived
        self.assertIn('#define ORBIT_RATE 36', cam)                    # one orbit in 10 s
        self.assertIn('if(!Q_strcasecmp(sub,"orbit")){orbit_command(n);return;}', cam)
        self.assertIn('orbit [photo] [speed DEG] [ref N / mark NAME]', doc.CATALOGUE.read_text(encoding='utf-8'))
        inspect = (SRC / 'aw_inspect.c').read_text(encoding='utf-8')
        self.assertIn('r=pick(&best,&st,&slot,&bounds,eye,dir,&limit);', inspect)   # dbg ent and the orbit share the pick


class Shots(unittest.TestCase):
    """dbg cam pan (also dbg pan cam) and dbg cam track (DBG-CAM-PAN-TRACK-68): film-style shots on the orbit's camera
    owner. The motion against time (holds, ease, constant middle, frame-time sequences, the speed word, the ending) is
    run natively in tests/aga_cam_test.c (EngineReader above); these keep the engine's parts joined."""

    def setUp(self):
        self.view = (SRC / 'aw_view.c').read_text(encoding='utf-8')
        self.cam = (SRC / 'aw_cam.c').read_text(encoding='utf-8')
        self.shots = self.view[self.view.index('/* ---- dbg cam pan and dbg cam track'):self.view.index('static void set_chase(int on);')]

    def section(self, text, start, end):
        return text[text.index(start):text.index(end)]

    def test_the_commands(self):
        pan = self.section(self.cam, 'static void pan_command(int argc)', 'static int mark_eye(')
        for word in ('"photo"', '"off"', '"speed"', '"hold"'):
            self.assertIn(word, pan)
        # DEGREES first (default 360, negative allowed), HOLD second (default 3 s at each end)
        self.assertIn('float degrees=360,hold=AW_CAM_SHOT_HOLD', pan)
        self.assertIn('number_arg(w,-AW_CAM_PAN_DEGREES_MAX,AW_CAM_PAN_DEGREES_MAX,&value)', pan)
        self.assertIn('numbers==1 && number_arg(w,0,AW_CAM_SHOT_HOLD_MAX,&value)', pan)
        # the default speed from the real field of view: the frame's width in 6 s (15 degrees a second at 90)
        self.assertIn('if(!speed)speed=AW_CamPanSpeed(r_refdef.fov_x);', pan)
        header = (SRC / 'aw_cam.h').read_text(encoding='utf-8')
        for text in ('#define AW_CAM_PAN_CROSS 6.0f', '#define AW_CAM_SHOT_HOLD 3.0f', '#define AW_CAM_SHOT_EASE 1.25f',
                     '#define AW_CAM_TRACK_SPEED 32.0f'):
            self.assertIn(text, header)
        self.assertIn('cvar_t scr_fov = {"fov","90"};', re.sub(r'\s+', ' ', (SRC / 'screen.c').read_text(encoding='latin-1')))
        track = self.section(self.cam, 'static void track_command(int argc)', '#define CAM_USAGE')
        for word in ('"forward"', '"to"', '"speed"', '"hold"', '"photo"', '"off"'):
            self.assertIn(word, track)
        self.assertIn('AW_CamTurn(r_refdef.viewangles[YAW],m.yaw)', track)       # the short way round to the mark's view
        self.assertIn('if(!mark_eye(p,&m,to))', track)                          # a mark on another map is refused
        for sub in ('"pan"', '"track"'):
            self.assertIn('if(!Q_strcasecmp(sub,%s))' % sub, self.cam)

    def test_a_negative_angle_pans_the_other_way(self):
        start = self.section(self.view, 'int AW_ViewPanStart(', 'int AW_ViewTrackStart(')
        self.assertIn('view_turn[1]=-degrees;', start)                            # Quake's yaw grows to the left
        self.assertIn('degrees<0?-degrees:degrees', start)                        # the distance is the size of the turn

    def test_one_writer_of_the_view(self):
        # the orbit's camera function is the one writer; a shot is a kind of it
        camera = self.section(self.view, 'static int orbit_camera(', 'int AW_ViewCamera(void) {')
        self.assertIn('if(orbit.kind!=AW_VIEW_CAM_ORBIT)return shot_camera();', camera)
        self.assertIn('if(orbit.active)return orbit_camera();', self.view)
        writers = re.findall(r'r_refdef\.(?:vieworg|viewangles)\[i\]=', self.view)
        self.assertEqual(len(writers), 2)                                         # shot_camera's position and angles
        # the commands read the view, never write it
        self.assertFalse(re.search(r'r_refdef\.(?:vieworg|viewangles)(?:\[\w+\])?\s*=[^=]', self.cam))
        self.assertNotIn(',r_refdef.vieworg)', self.cam)
        self.assertNotIn(',r_refdef.viewangles)', self.cam)
        # the shots use the orbit's detachment and its end; nothing allocated, nothing per frame when none runs
        self.assertIn('camera_detach(p);', self.shots)
        for text in ('malloc', 'AW_TryMalloc', 'Hunk_', 'Z_Malloc'):
            self.assertNotIn(text, self.shots)
        frame = self.section(self.view, 'static void orbit_frame(float dt,int forced) {', 'static int orbit_key(int key) {')
        self.assertIn('if(orbit.active && orbit.kind!=AW_VIEW_CAM_ORBIT){shot_frame(dt);return;}', frame)

    def test_the_timeline_and_the_endings(self):
        frame = self.section(self.view, 'static void shot_frame(float dt) {', 'static void orbit_frame(')
        self.assertIn('if(playing())AW_CamShotStep(&orbit.shot,dt);', frame)     # the clock runs while the game is played
        self.assertIn('if(AW_CamShotDone(&orbit.shot))AW_ViewOrbitEnd(1);', frame)   # it ends by itself after the hold
        self.assertIn('VectorCopy(orbit.view,cl.viewangles);', frame)            # the mouse does not move a shot
        # Esc or right click ends it early; every other game key does nothing
        key = self.section(self.view, 'static int orbit_key(', 'static int shot_camera(')
        self.assertIn('if(orbit.kind!=AW_VIEW_CAM_ORBIT){if(key==K_ESCAPE || key==K_MOUSE2)AW_ViewOrbitEnd(1);return 1;}', key)
        end = self.section(self.view, 'void AW_ViewOrbitEnd(', '/* dbg cam orbit mark NAME')
        self.assertIn('done?"ended":"stopped early"', end)
        # the lines a session script waits on: "Camera pan ended" / "Camera track ended"
        self.assertIn('"Camera %s %s: position, view, movement and flags restored.\\n"', end)
        self.assertIn('kind==AW_VIEW_CAM_PAN?"pan":"track"', self.shots)
        # dbg cam pan off / dbg cam track off end a running shot
        self.assertIn('static int shot_off(const char *what) {', self.cam)

    def test_nothing_on_the_screen(self):
        say = self.section(self.view, 'static void shot_say(const char *text) {', 'static const char *shot_name(')
        self.assertIn('con_notify_quiet=1;Con_Printf("%s",text);con_notify_quiet=0;', say)
        self.assertIn('con_notify_quiet ? 0 : realtime', (SRC / 'console.c').read_text(encoding='latin-1'))
        self.assertNotIn('AW_UISubtitle', self.shots)
        self.assertEqual(self.shots.count('shot_say(line);'), 1)                 # the start line
        self.assertIn('shot_say(line);', self.section(self.view, 'void AW_ViewOrbitEnd(', '/* dbg cam orbit mark NAME'))
        self.assertIn('static void quiet_line(const char *line) {con_notify_quiet=1;Con_Printf("%s",line);con_notify_quiet=0;}',
                      self.cam)
        for name in ('pan_command', 'track_command'):
            command = self.cam[self.cam.index('static void %s(int argc)' % name):]
            command = command[:command.index('\n}\n')]
            self.assertIn('quiet_line(line);', command)

    def test_the_body_in_third_person(self):
        start = self.section(self.view, 'static int shot_start(', 'int AW_ViewPanStart(')
        self.assertIn('int keep_body=orbit.active?orbit.body:owned && view.mode!=AW_VIEW_FIRST && body_ready();', start)
        self.assertIn('VectorCopy(r_refdef.vieworg,orbit.from);', start)          # the view's own point: a tripod
        self.assertIn('VectorCopy(r_refdef.viewangles,orbit.start_angles);orbit.start_angles[ROLL]=0;', start)

    def test_one_easing_curve_with_the_halloween_director(self):
        ease = (SRC / 'aw_ease.h').read_text(encoding='utf-8')
        self.assertIn('return t * t * (3 - 2 * t);', ease)
        rules = (SRC / 'aw_halloween_rules.c').read_text(encoding='utf-8')
        self.assertIn('*u=AW_EaseSmooth(t);', rules)
        self.assertNotIn('t*t*(3-2*t)', rules)
        cam_rules = (SRC / 'aw_cam_rules.c').read_text(encoding='utf-8')
        self.assertIn('#include "aw_ease.h"', cam_rules)
        self.assertEqual(cam_rules.count('AW_EaseSmoothArea('), 2)                # the ramp in, its mirror out

    def test_listed_with_the_other_cameras(self):
        rows = {words: help_text for _, words, handler, help_text in doc.entries(doc.CATALOGUE.read_text(encoding='utf-8'))}
        self.assertIn('/ pan / track]', rows['cam'])
        self.assertTrue(rows['cam pan'].startswith('[DEGREES] [HOLD] [speed DEG] [photo] / off:'))
        self.assertTrue(rows['cam track'].startswith('[SPEED] forward N / to MARK [HOLD] [speed U] [photo] / off:'))
        self.assertEqual(rows['pan cam'], 'same as cam pan')
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('| `dbg cam pan` | `dbg pan cam` |', page)
        self.assertIn('| `dbg cam track` | - |', page)
        marks = (ROOT / 'docs' / 'CAMERA_MARKS.md').read_text(encoding='utf-8')
        for text in ('## Pan', '## Track', '`dbg pan cam`', '`dbg cam pan 180 5`', 'saw 60 Camera pan ended'):
            self.assertIn(text, marks)
        console = (SRC / 'aw_console.c').read_text(encoding='utf-8')
        self.assertIn('(!strcmp(r->command,"aw_cam") && !strncmp(r->words,"cam ",4))', console)
        self.assertIn('if(!strcmp(r->command,"aw_cam") && !strcmp(r->words,"pan cam")){', console)


class Staging(unittest.TestCase):
    def test_the_builder_copies_the_public_marks(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            receipt = build_aga.stage_debug_catalogues(Path(tmp))
            self.assertEqual((Path(tmp) / 'camera-marks.txt').read_bytes(), camera_marks.PUBLIC.read_bytes())
            self.assertEqual(receipt['camera-marks.txt']['bytes'], len(camera_marks.PUBLIC.read_bytes()))

    def test_invalid_marks_stop_the_staging(self):
        import build_aga
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir()
            for name in ('debug-commands.txt', 'shroompicker.txt'):
                shutil.copy(build_aga.ROOT / 'config' / name, root / 'config' / name)
            (root / 'config' / 'camera-marks.txt').write_bytes(b'AWCM1\nbm1|global|1|0 0|-|-|-|\n')
            target = root / 'id1'
            target.mkdir()
            with patch.object(build_aga, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'camera marks.*position'):
                    build_aga.stage_debug_catalogues(target)
            self.assertEqual(list(target.iterdir()), [])

    def test_shipped_as_a_project_catalogue(self):
        import json
        self.assertIn('config/camera-marks.txt', json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        self.assertIn('"config/camera-marks.txt"', (ROOT / 'tools' / 'release.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
