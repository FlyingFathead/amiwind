#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Engine boot + map-load smoke in FS-UAE (CHIM-DEV3-MAPLOAD-CRASH-36).

Puts an engine binary into a FRESH copy of a finished image's boot disk and runs that copy in FS-UAE (68040, the
accelerated JIT preset by default) in a throwaway offline container: boot to the console, load a map with the music
on and play, check the music stream reads, `dbg music off`, load a second map, `dbg music on`, check it reads again.
The emulator dying, the game clock stopping or any step missing fails the smoke (exit 1).

Nothing of the image is changed: the boot disk is copied (sparse) into a scratch folder of a Docker volume, the world
disk is mounted read-only from the image, and the scratch folder is removed afterwards (also on failure).

Usage (paths inside VOLUME are relative to its root):
  engine_smoke.py --engine FILE --volume VOLUME --image-dir DIR --scratch DIR --roms HOST_DIR --out HOST_DIR
                  [--prof jit|interp] [--map seyda] [--tp "-21800 -12300"] [--play 10]
                  [--builder-image IMAGE] [--fsuae-image IMAGE] [--cpus 2] [--cpu-shares N] [--name NAME]
The builder image needs xdftool (amitools) at /opt/amiwind-tools/venv/bin/xdftool; the FS-UAE image (emulator side: PROBE below) needs fs-uae,
Xvfb, xdotool and ffmpeg. Images are used as present (--pull never); containers run with --network none.
Exit: 0 pass, 1 smoke failed, 2 setup failed. The last output line is "smoke-exit=N" and the line before it the result.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
XDF = '/opt/amiwind-tools/venv/bin/xdftool'

# The emulator side, written to OUT/probe.sh and run with sh inside the FS-UAE container.
PROBE = r'''#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Engine boot + map-load smoke, emulator side (tools/engine_smoke.py starts it in a throwaway offline FS-UAE container).
# Mounts: /w = the run's fresh boot-disk copy (play-boot.hdf), /img = the image folder (world disk, read-only),
# /roms = the owner's Kickstart folder (read-only), /out = this run's output folder.
# Env: WORLD (world disk file name in /img, may be empty), PROF jit|interp, KICK (Kickstart file name in /roms),
# MAP1 (first map, default seyda), AFTER (after it loads: a console command, or key:NAME, e.g. key:Return for a MiniWind), TP (second load as "dbg tp X Y", default Balmora), PLAY (seconds of play, 10).
# TP "same X Y": a one-area image; teleport inside MAP1 and stay in it (no second map). TP "view X Y Z": noclip and
# aw_view to a local point of MAP1; the client's view origin must arrive there (wide network coordinates).
# START enter: press Enter on a MiniWind startup screen and through its quick character pages instead of "map MAP1".
# Steps, each judged: boot to the remote-control console; load MAP1 with the music on and play; the music stream
# reads (aw_music_status reads=); dbg music off (no more reads, the game goes on); a second load (TP) with the music
# off; dbg music on (reads again). Any emulator exit, stall or missing step fails. Last line: "smoke RESULT ...".
R=/out; mkdir -p $R/logs $R/shots $R/home $R/awctl
PROF=${PROF:-jit}; MAP1=${MAP1:-seyda}; TP=${TP:--21800 -12300}; PLAY=${PLAY:-10}; KICK=${KICK:-kickstart-3.1-a1200.rom}
N=$((60 + $(od -An -N1 -tu1 /dev/urandom)))
cat > $R/smoke.fs-uae <<CFG
[config]
amiga_model = A1200
cpu = 68040-NOMMU
fpu = 68040
uae_cpu_24bit_addressing = false
chip_memory = 2048
slow_memory = 0
fast_memory = 0
zorro_iii_memory = 16384
kickstart_file = /roms/$KICK
hard_drive_0 = /w/play-boot.hdf
hard_drive_0_type = hdf
hard_drive_2 = $R/awctl
hard_drive_2_label = AWCTL
hard_drive_2_priority = -128
joystick_port_1 = none
floppy_drive_volume = 0
fullscreen = 0
window_width = 800
window_height = 600
initial_input_grab = 0
automatic_input_grab = 0
screenshots_output_dir = $R/shots
base_dir = $R/home
CFG
if [ -n "${WORLD:-}" ]; then
  printf 'hard_drive_1 = /img/%s\nhard_drive_1_type = hdf\nhard_drive_1_read_only = 1\n' "$WORLD" >> $R/smoke.fs-uae
fi
K=1
if [ "$PROF" = interp ]; then printf 'jit_compiler = 0\nuae_cpu_speed = max\n' >> $R/smoke.fs-uae; K=3
else printf 'jit_compiler = 1\nuae_cpu_speed = max\n' >> $R/smoke.fs-uae; fi
# ILLEGAL=1: FS-UAE logs the 68k PC of every access to unmapped memory (use with PROF interp; JOB_PREAMBLE 53)
[ "${ILLEGAL:-0}" = 1 ] && printf 'uae_log_illegal_mem = 1\n' >> $R/smoke.fs-uae
export HOME=$R/home DISPLAY=:$N LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe SDL_AUDIODRIVER=dummy
Xvfb :$N -screen 0 1024x768x24 -nolisten tcp > $R/logs/xvfb.log 2>&1 &
XP=$!; sleep 2
fs-uae $R/smoke.fs-uae > $R/logs/fsuae.log 2>&1 &
FP=$!
log(){ echo "$(date -u +%T) $*" | tee -a $R/logs/steps.log; }
alive(){ kill -0 $FP 2>/dev/null; }
win(){ xdotool search --name "FS-UAE" 2>/dev/null | head -1; }
con(){ W=$(win); xdotool windowfocus --sync $W 2>/dev/null; xdotool key --clearmodifiers F10; sleep 1
  xdotool type --clearmodifiers --delay 40 -- "$1"; sleep 0.3; xdotool key --clearmodifiers Return; }
key(){ W=$(win); xdotool windowfocus --sync $W 2>/dev/null; xdotool key --clearmodifiers "$1"; }
# xdo ARGS: raw xdotool steps in the emulator window (mouse buttons, held qualifiers), e.g.
# "keydown Super_L mousedown 1 mousemove_relative 0 120 mouseup 1 keyup Super_L"
xdo(){ W=$(win); xdotool windowfocus --sync $W 2>/dev/null; xdotool $1; }
rc(){ i=0; while [ -e $R/awctl/cmd.txt ] && [ $i -lt 40 ]; do sleep 0.5; i=$((i+1)); done
  printf '%s\n' "$1" > $R/awctl/cmd.txt.tmp && mv $R/awctl/cmd.txt.tmp $R/awctl/cmd.txt; log "cmd $1"; }
shot(){ ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -video_size 1024x768 -i :$N -frames:v 1 $R/shots/$1.png 2>/dev/null; }
# st KEY: one value of the game's state file. The game rewrites the file in place, so a read can catch it half
# written (gate 1907: "realtime 62.10 -> " empty). Only a copy that ends with its "end" line counts; else read again
# (up to 20 times, 0.2 s apart) before giving up with an empty value.
st(){ i=0; while [ $i -lt ${STATE_TRIES:-20} ]; do cp $R/awctl/state.txt $R/state.read 2>/dev/null
    if [ "$(tail -n 1 $R/state.read 2>/dev/null)" = end ]; then
      awk -v k="$1" '$1==k{$1="";sub(/^ /,"");print}' $R/state.read; return 0; fi
    sleep 0.2; i=$((i+1)); done; }
reads(){ grep -o 'reads=[0-9]*' $R/awctl/console.log 2>/dev/null | tail -1 | cut -d= -f2; }
# The engine's efrag safety net keeps the game running; a smoke still fails when it was used (CHIM-FRAME-EDGE-EFRAG-CRASH-36).
finish(){ case "$1" in PASS*) b=$(st efrags_bad); [ -n "$b" ] && [ "$b" != 0 ] && set -- "FAIL efrag safety net used $b times (console: Efrag safety net)"
    [ "$(st screen)" = game ] || set -- "FAIL the run ended outside play: screen $(st screen) (map $(st map))";; esac
  cp $R/home/Cache/Logs/fs-uae.log.txt $R/logs/fs-uae.log.txt 2>/dev/null
  grep -E "Caught illegal|Fault address|Suspicious" $R/logs/fs-uae.log.txt 2>/dev/null | tail -12 > $R/logs/emulator-faults.txt
  cp $R/awctl/console.log $R/logs/console.log 2>/dev/null; alive && shot final
  kill $FP 2>/dev/null; sleep 2; kill $XP 2>/dev/null; log "smoke RESULT $1"; exit 0; }
# play S: S seconds of game time; the emulator must stay up and the game clock must move
play(){ r1=$(st realtime); s=0
  while [ $s -lt $(($1*K)) ]; do alive || finish "FAIL emulator exited during $2 (map $(st map))"; sleep 1; s=$((s+1)); done
  r2=$(st realtime); [ -n "$r2" ] && [ "$r1" != "$r2" ] || finish "FAIL game stalled during $2 (realtime $r1 -> $r2)"; }
# inplay WHAT: the map is in play, not only loaded under a menu (SMOKE-PASSES-WITHOUT-MAP-36): within 30 s the
# client has its world (signon 4, world leaves) and the screen is the game. An engine without these state lines fails.
inplay(){ s=0; while [ $s -lt $((30*K)) ]; do alive || finish "FAIL emulator exited before $1 was in play"
    [ "$(st screen)" = game ] && [ "$(st signon)" = 4 ] && [ "$(st world_leafs)" -gt 0 ] 2>/dev/null && { log "in play: $1 (map $(st map), $(st world_leafs) leaves, local $(st local))"; return 0; }
    sleep 1; s=$((s+1)); done
  finish "FAIL $1 is not in play: screen $(st screen), signon $(st signon), world leaves $(st world_leafs) (map $(st map))"; }
# loaded SERVER: wait (max 150 s) for the map to run
loaded(){ s=0; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited loading $1";
  [ "$(st server)" = "$1" ] && return 0; sleep 1; s=$((s+1)); done; finish "FAIL $1 did not load (server $(st server))"; }
t0=$(date +%s)
sleep $((9*K))
n=0; while [ ! -s $R/awctl/state.txt ] && [ $n -lt $((200*K)) ]; do
  alive || finish "FAIL emulator exited during boot"; con "aw_remote 1"; sleep 2; key Escape; sleep $((8*K)); n=$((n+2+8*K)); done
[ -s $R/awctl/state.txt ] || finish "FAIL no remote control after boot"
log "boot: remote up after $(( $(date +%s) - t0 )) s"; shot menu
if [ "${START:-map}" = enter ] || [ "${START:-map}" = auto ]; then  # a MiniWind image starts its own scene; Enter through its quick character pages
  [ "${START:-map}" = auto ] || key Return; loaded "$MAP1"; i=0  # until the view renders (local origin not 0 0 0), at most 20 pages
  while [ "${START:-map}" != auto ] && [ $i -lt 20 ] && { [ "$(st map)" = none ] || [ "$(st local)" = "0 0 0" ]; }; do sleep $((2*K)); key Return; i=$((i+1)); done
  sleep $((2*K)); [ "$(st map)" != none ] && [ "$(st local)" != "0 0 0" ] || finish "FAIL $MAP1 runs but the game never started (client map $(st map))"
  log "in game after $i Enter presses: local $(st local)"
else rc "map $MAP1"; loaded "$MAP1"; case "$AFTER" in key:*) sleep $((3*K)); key "${AFTER#key:}"; log "after load: key ${AFTER#key:}";; ?*) rc "$AFTER"; log "after load: $AFTER";; esac; fi
inplay "$MAP1"
play $PLAY "$MAP1 (music on)"; shot map1
# SCRIPT: a scripted session instead of the music and second-load steps (evidence shots, replays). One step per line:
# "cmd TEXT" console command, "key NAME" key press, "xdo ARGS" raw xdotool steps (mouse, held keys), "wait S" S seconds of game time (the game must keep running),
# "shot NAME" screenshot shots/NAME.png, "state KEY" logs that state value; other lines are comments. Ends PASS
# when the game survives the whole script.
if [ -s $R/script.txt ]; then
  while IFS= read -r line <&3 || [ -n "$line" ]; do  # fd 3: ffmpeg (shot) reads stdin
    case "$line" in
    cmd\ *) rc "${line#cmd }";;
    key\ *) key "${line#key }"; log "key ${line#key }";;
    xdo\ *) xdo "${line#xdo }"; log "xdo ${line#xdo }";;
    wait\ *) play "${line#wait }" "script ($(st map))";;
    shot\ *) shot "${line#shot }"; log "shot ${line#shot } at local $(st local)";;
    state\ *) log "state ${line#state }: $(st ${line#state })";;
    esac
    alive || finish "FAIL emulator exited after script step: $line"
  done 3< $R/script.txt
  [ "$(st screen)" = game ] && [ "$(st signon)" = 4 ] && [ "$(st world_leafs)" -gt 0 ] 2>/dev/null ||
    finish "FAIL scripted run ended outside play: map $(st map), signon $(st signon), world leaves $(st world_leafs)"
  finish "PASS script, $(st map) running, $(( $(date +%s) - t0 )) s"
fi
rc "aw_music_status"; sleep $((3*K)); a=$(reads); sleep $((5*K)); rc "aw_music_status"; sleep $((3*K)); b=$(reads)
[ -n "$a" ] && [ -n "$b" ] && [ "$b" -gt "$a" ] || finish "FAIL music not reading in $MAP1 (reads $a -> $b)"
log "music on: reads $a -> $b"
rc "aw_music_status off"; sleep $((3*K)); grep -q "Background music off" $R/awctl/console.log || finish "FAIL dbg music off not confirmed"
play 5 "music off"; rc "aw_music_status"; sleep $((3*K)); e=$(reads)
case "$TP" in
same\ *)  # a one-area image (MiniWind of one CHIM frame): teleport inside MAP1 (e.g. past the narrow +/-4,096 range)
  rc "dbg tp ${TP#same }"; sleep $((10*K)); alive || finish "FAIL emulator exited after dbg tp ${TP#same }"
  [ "$(st server)" = "$MAP1" ] || finish "FAIL dbg tp ${TP#same } left $MAP1 (server $(st server))";;
view\ *)  # a one-area image: noclip and aw_view to a LOCAL point X Y Z of MAP1; the client view must arrive there,
  # through the network coordinates (a narrow engine wraps past +/-4,096)
  set -- ${TP#view }; rc "noclip"; sleep $((2*K)); rc "aw_view $1 $2 $3 ${4:-0} 0"; sleep $((10*K))
  alive || finish "FAIL emulator exited after aw_view $1 $2 $3"
  [ "$(st server)" = "$MAP1" ] || finish "FAIL aw_view left $MAP1 (server $(st server))"
  set -- $1 $2 $(st local); dx=$(( $3 - $1 )); dy=$(( $4 - $2 ))
  [ ${dx#-} -le 64 ] && [ ${dy#-} -le 64 ] || finish "FAIL view at local $3 $4, not $1 $2 (network coordinates)"
  log "view: local $3 $4 (asked $1 $2)";;
map:*)  # a one-town image: the second load is another map it holds
  rc "map ${TP#map:}"; s=0; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited after map ${TP#map:}";
  [ "$(st server)" != "$MAP1" ] && [ -n "$(st server)" ] && [ "$(st server)" != none ] && break; sleep 1; s=$((s+1)); done
[ $s -lt $((150*K)) ] || finish "FAIL map ${TP#map:} did not load a map (server $(st server))";;
*)
rc "dbg tp $TP"; s=0; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited after dbg tp $TP";
  [ "$(st server)" != "$MAP1" ] && [ -n "$(st server)" ] && [ "$(st server)" != none ] && break; sleep 1; s=$((s+1)); done
[ $s -lt $((150*K)) ] || finish "FAIL dbg tp $TP did not load a map (server $(st server))";;
esac
inplay "the second load ($(st server))"
play $PLAY "$(st server) (music off)"; shot map2
rc "aw_music_status"; sleep $((3*K)); c=$(reads)
[ "$c" = "$e" ] || finish "FAIL music read while off (reads $e -> $c)"
rc "aw_music_status on"; sleep $((8*K)); rc "aw_music_status"; sleep $((3*K)); d=$(reads)
[ -n "$d" ] && [ "$d" -gt "${c:-0}" ] || finish "FAIL music did not read again after dbg music on (reads $c -> $d)"
play 5 "music on again"
finish "PASS boot, $MAP1 and $(st server) loaded, music reads $a -> $b, off (reads stayed $c), on again ($c -> $d), $(( $(date +%s) - t0 )) s"
'''


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def docker(*args, check=True, capture=True):
    env = dict(os.environ, MSYS_NO_PATHCONV='1')
    return subprocess.run(['docker', *args], env=env, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None, stderr=subprocess.STDOUT if capture else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--engine', required=True, type=Path)
    ap.add_argument('--volume', required=True)
    ap.add_argument('--image-dir', required=True, help='image folder inside the volume (holds *.hdf)')
    ap.add_argument('--scratch', required=True, help='scratch folder inside the volume (created, then removed)')
    ap.add_argument('--roms', required=True, type=Path)
    ap.add_argument('--kickstart', default='kickstart-3.1-a1200.rom')
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--prof', choices=('jit', 'interp'), default='jit')
    ap.add_argument('--map', default='seyda')
    ap.add_argument('--tp', default='-21800 -12300',
                    help='second load as dbg tp X Y (default Balmora); "same X Y" for a one-area image: teleport inside --map; '
                         '"view X Y Z": noclip + aw_view to a local point of --map, checked on the client; map:NAME: a second map the image holds')
    ap.add_argument('--play', type=int, default=10)
    ap.add_argument('--after-load', default='', help='sent once the first map is loaded: a console command, or key:NAME for a key press, '
                    'e.g. key:Return for a MiniWind image, which holds its startup screen until Enter')
    ap.add_argument('--log-illegal', action='store_true',
                    help='FS-UAE logs the 68k PC of every unmapped memory access (uae_log_illegal_mem; with --prof interp)')
    ap.add_argument('--start', choices=('map', 'enter', 'auto'), default='map',
                    help='map: load --map from the console (default); enter: press Enter on a MiniWind startup screen, which starts '
                         'its own scene (--map names the map it must load)')
    ap.add_argument('--script', type=Path,
                    help='a scripted session after the first map (cmd/key/xdo/wait/shot/state lines) instead of the music '
                         'and second-load steps: evidence shots and replays')
    ap.add_argument('--builder-image', default='amiwind-builder:v0.0.35-clean')
    ap.add_argument('--fsuae-image', default='amiwind-fsuae:3.1.66-ubuntu24.04-eval1')
    ap.add_argument('--cpus', default='2')
    ap.add_argument('--cpu-shares', default='')
    ap.add_argument('--name', default='aw-engine-smoke')
    args = ap.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9._/-]+', args.image_dir + args.scratch) or '..' in args.scratch \
            or not args.scratch.strip('/'):
        print('engine smoke: image dir and scratch must be plain relative paths')
        print('smoke-exit=2')
        return 2
    if not args.engine.is_file() or not (args.roms / args.kickstart).is_file():
        print('engine smoke: engine or Kickstart missing')
        print('smoke-exit=2')
        return 2
    want = sha256(args.engine)
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(args.engine, out / 'engine.AmiWind')
    (out / 'probe.sh').write_text(PROBE, encoding='utf-8', newline='\n')
    if args.script:
        shutil.copyfile(args.script, out / 'script.txt')
    (out / 'engine.txt').write_text('engine sha256 %s\nimage %s\nprofile %s\n' % (want, args.image_dir, args.prof),
                                    encoding='utf-8', newline='\n')
    shares = ['--cpu-shares', args.cpu_shares] if args.cpu_shares else []
    base = ['run', '--pull', 'never', '--rm', '--network', 'none', *shares]
    scratch = args.scratch.strip('/')
    prep = f'''set -e
rm -rf /vol/{scratch}; mkdir -p /vol/{scratch}
B=$(ls /vol/{args.image_dir}/*.hdf | grep -v world | head -1); [ -n "$B" ]
cp --sparse=always "$B" /vol/{scratch}/play-boot.hdf; chmod u+w /vol/{scratch}/play-boot.hdf
W=$(ls /vol/{args.image_dir}/*world-01.hdf 2>/dev/null | head -1 || true); echo "world=$(basename "$W" 2>/dev/null)"
X={XDF}; D=/vol/{scratch}/play-boot.hdf
$X $D open part=DH0 + delete AmiWind + write /t/engine.AmiWind AmiWind
printf 'aw_remote 1\\n' > /tmp/autoexec.cfg
$X $D open part=DH0 + delete id1/autoexec.cfg + write /tmp/autoexec.cfg id1/autoexec.cfg
$X $D open part=DH0 + read AmiWind /tmp/back
echo "readback=$(sha256sum /tmp/back | cut -d' ' -f1)"'''

    def cleanup():
        docker(*base, '--cpus', '1', '--memory', '256m', '--user', '1000:1000', '--name', args.name + '-clean',
               '-v', f'{args.volume}:/vol', args.builder_image, 'sh', '-c', f'rm -rf /vol/{scratch}', check=False)
    try:
        r = docker(*base, '--cpus', '1', '--memory', '2g', '--user', '1000:1000', '--name', args.name + '-prep',
                   '-v', f'{args.volume}:/vol', '-v', f'{out}:/t:ro', args.builder_image, 'sh', '-c', prep,
                   check=False)
        (out / 'prep.log').write_text(r.stdout, encoding='utf-8', newline='\n')
        world = re.search(r'^world=(\S*)', r.stdout, re.M)
        back = re.search(r'^readback=([0-9a-f]{64})', r.stdout, re.M)
        if r.returncode or not back or back.group(1) != want:
            print('engine smoke: preparing the play copy failed (see prep.log)')
            print('smoke-exit=2')
            return 2
        docker(*base, '--cpus', args.cpus, '--memory', '3g', '--name', args.name + '-run', '--entrypoint', 'sh',
               '-e', f'PROF={args.prof}', '-e', f'WORLD={world.group(1) if world else ""}', '-e', f'MAP1={args.map}',
               '-e', f'TP={args.tp}', '-e', f'PLAY={args.play}', '-e', f'START={args.start}', '-e', f'AFTER={args.after_load}', '-e', f'ILLEGAL={int(args.log_illegal)}', '-e', f'KICK={args.kickstart}',
               '--mount', f'type=volume,src={args.volume},dst=/w,volume-subpath={scratch}',
               '--mount', f'type=volume,src={args.volume},dst=/img,volume-subpath={args.image_dir},readonly',
               '-v', f'{args.roms.resolve()}:/roms:ro', '-v', f'{out}:/out', args.fsuae_image, '/out/probe.sh',
               check=False, capture=False)
    finally:
        cleanup()
    steps = (out / 'logs' / 'steps.log')
    lines = steps.read_text(encoding='utf-8', errors='replace').splitlines() if steps.is_file() else []
    result = next((l for l in reversed(lines) if 'smoke RESULT' in l), 'smoke RESULT FAIL no result line')
    print(result.split('smoke RESULT ', 1)[1] if 'smoke RESULT ' in result else result)
    code = 0 if 'smoke RESULT PASS' in result else 1
    print('smoke-exit=%d' % code)
    return code


if __name__ == '__main__':
    sys.exit(main())
