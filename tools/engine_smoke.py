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
                  [--prof jit|interp] [--fast-mb 32] [--map seyda] [--tp "-21800 -12300"] [--play 10] [--repeat 3]
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
IDE_CYLINDER_BYTES = 16 * 63 * 512      # an IDE port reads whole cylinders (IMAGE-IDE-CYLINDER-TAIL-59)
# The maintainer, 2026-10-27 17:24 +0200 / 2026-10-27 15:24 UTC:"WE RUN AT 32MB FAST BY DEFAULT FROM NOW ON" (the game's minimum)
DEFAULT_FAST_MB = 32

# The emulator side, written to OUT/probe.sh and run with sh inside the FS-UAE container.
PROBE = r'''#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Engine boot + map-load smoke, emulator side (tools/engine_smoke.py starts it in a throwaway offline FS-UAE container).
# Mounts: /w = the run's fresh boot-disk copy (play-boot.hdf), /img = the image folder (world disk, read-only),
# /roms = the maintainer's Kickstart folder (read-only), /out = this run's output folder.
# Env: WORLD (world disk file name in /img, may be empty), PROF jit|interp, KICK (Kickstart file name in /roms),
# FASTMB (Zorro III Fast RAM in MiB, default 32 = the game's minimum since 27 October 2026, the maintainer's order; 128 = a playtest's default),
# MAP1 (first map, default seyda), REPEAT (how many times the TP map change runs, default 3), AFTER (after it loads: a console command, or key:NAME, e.g. key:Return for a MiniWind), TP (second load as "dbg tp X Y", default Balmora), PLAY (seconds of play, 10).
# TP "same X Y": a one-area image; teleport inside MAP1 and stay in it (no second map). TP "view X Y Z": noclip and
# aw_view to a local point of MAP1; the client's view origin must arrive there (wide network coordinates).
# START enter: press Enter on a MiniWind startup screen and through its quick character pages instead of "map MAP1";
# with MAP1 any the map the image starts on is taken, whichever it is.
# Steps, each judged: boot to the remote-control console; load MAP1 with the music on and play; the music stream
# reads (aw_music_status reads=); dbg music off (no more reads, the game goes on); a second load (TP) with the music
# off; dbg music on (reads again). Any emulator exit, stall or missing step fails. Last line: "smoke RESULT ...".
R=/out; mkdir -p $R/logs $R/shots $R/home $R/awctl
PROF=${PROF:-jit}; MAP1=${MAP1:-seyda}; TP=${TP:--21800 -12300}; PLAY=${PLAY:-10}; REPEAT=${REPEAT:-3}; KICK=${KICK:-kickstart-3.1-a1200.rom}; FASTMB=${FASTMB:-32}
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
zorro_iii_memory = $((FASTMB * 1024))
kickstart_file = /roms/$KICK
hard_drive_0 = /w/play-boot.hdf
hard_drive_0_type = hdf
hard_drive_0_controller = ide0
joystick_port_1 = none
floppy_drive_volume = 0
fullscreen = 0
window_width = 800
window_height = 600
initial_input_grab = 0
automatic_input_grab = 0
console_debugger = 1
modifier_key = key_lalt
screenshots_output_dir = $R/shots
base_dir = $R/home
CFG
# REMOTE=0 (--remote off, experiment E2 of CHIM-SEYDA-BALMORA-LOAD-HANG-43): no remote-console folder (AWCTL) at all,
# as in a player's game; the route then runs from the play copy's autoexec and is judged by screenshots
[ "${REMOTE:-1}" = 0 ] || printf 'hard_drive_2 = %s\nhard_drive_2_label = AWCTL\nhard_drive_2_priority = -128\n' "$R/awctl" >> $R/smoke.fs-uae
if [ -n "${WORLD:-}" ]; then
  printf 'hard_drive_1 = /img/%s\nhard_drive_1_type = hdf\nhard_drive_1_read_only = 1\nhard_drive_1_controller = ide1\n' "$WORLD" >> $R/smoke.fs-uae
fi
K=1
if [ "$PROF" = interp ]; then printf 'jit_compiler = 0\nuae_cpu_speed = max\n' >> $R/smoke.fs-uae; K=3
else printf 'jit_compiler = 1\nuae_cpu_speed = max\n' >> $R/smoke.fs-uae; fi
# ILLEGAL=1: FS-UAE logs the 68k PC of every access to unmapped memory (use with PROF interp; JOB_PREAMBLE 53)
[ "${ILLEGAL:-0}" = 1 ] && printf 'uae_log_illegal_mem = 1\n' >> $R/smoke.fs-uae
# --emu-option KEY=VALUE (experiment E3: e.g. deterministic=1): extra emulator lines, checked in the start-up log
[ -s $R/emu-options.txt ] && cat $R/emu-options.txt >> $R/smoke.fs-uae
export HOME=$R/home DISPLAY=:$N LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe SDL_AUDIODRIVER=dummy
Xvfb :$N -screen 0 1024x768x24 -nolisten tcp > $R/logs/xvfb.log 2>&1 &
XP=$!; sleep 2
# FS-UAE on a pseudo-terminal with its monitor (console_debugger) fed from a FIFO: a stalled load is examined in
# place (stall.py, CHIM-SEYDA-BALMORA-LOAD-HANG-43). Without script(1) it runs as before, without the monitor.
rm -f $R/dbg.in; mkfifo $R/dbg.in
if command -v script >/dev/null; then (exec 7<>$R/dbg.in; exec script -qfc "fs-uae --stdout $R/smoke.fs-uae" $R/logs/fsuae.log <&7 >/dev/null 2>&1) &
else fs-uae $R/smoke.fs-uae > $R/logs/fsuae.log 2>&1 & fi
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
# rc TEXT: one remote-control command. The game takes the previous one first; one it has not taken in RC_WAIT
# seconds (60, a loaded host's margin) means the game stopped answering: examined as a stall (SMOKE-MUSIC-REREAD-
# FLAKY-57: gates 5037, 5044, 5092 and 5093 had the game stop writing its state and taking commands a few seconds after
# a load, and the next check, the music's, failed with a misleading message).
rc(){ i=0; while [ -e $R/awctl/cmd.txt ] && [ $i -lt $((${RC_WAIT:-60}*2*K)) ]; do sleep 0.5; i=$((i+1)); done
  [ -e $R/awctl/cmd.txt ] && stall "the game stopped taking commands: '$(cat $R/awctl/cmd.txt)' not taken in ${RC_WAIT:-60} s, before '$1' (state last written $(date -u -r $R/awctl/state.txt +%T 2>/dev/null), map $(st map))"
  printf '%s\n' "$1" > $R/awctl/cmd.txt.tmp && mv $R/awctl/cmd.txt.tmp $R/awctl/cmd.txt; log "cmd $1"; }
# status: a fresh aw_music_status answer's reads= value: waits (up to 30 s) for a NEW status line, never takes the
# previous one (a loaded host answers late); empty when no new line came
status(){ n0=$(grep -c 'reads=' $R/awctl/console.log 2>/dev/null); rc "aw_music_status" >/dev/null; s=0   # log() tees: keep its line out of the value
  while [ $s -lt $((30*K)) ]; do [ "$(grep -c 'reads=' $R/awctl/console.log 2>/dev/null)" -gt "${n0:-0}" ] && { reads; return 0; }
    sleep 1; s=$((s+1)); done; }
# advance FROM: fresh status answers until reads pass FROM, over a window of MUSIC_WAIT seconds (45: a loaded host);
# the last value (or empty) when they never did. Strict: the stream must read on; only the waiting is longer.
advance(){ until_t=$(( $(date +%s) + ${MUSIC_WAIT:-45}*K )); v=
  while [ $(date +%s) -lt $until_t ]; do v=$(status); [ -n "$v" ] && [ "$v" -gt "${1:-0}" ] && break; sleep $((2*K)); done
  echo "$v"; }
shot(){ ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -video_size 1024x768 -i :$N -frames:v 1 $R/shots/$1.png 2>/dev/null; }
# rec NAME / recstop: an H.264 clip of the screen (shots/NAME.mp4, RECFPS frames a second, RECCRF quality; no
# audio: the emulator's sound goes to the dummy driver) while the script goes on; finish stops it.
RP=
rec(){ [ -z "$RP" ] || recstop; ffmpeg -loglevel error -y -f x11grab -draw_mouse 0 -framerate ${RECFPS:-15} -video_size 1024x768 -i :$N \
  -c:v libx264 -preset veryfast -crf ${RECCRF:-30} -pix_fmt yuv420p -movflags +faststart $R/shots/$1.mp4 < /dev/null > $R/logs/rec-$1.log 2>&1 &
  RP=$!; log "rec $1"; }
recstop(){ [ -n "$RP" ] || return 0; kill -INT $RP 2>/dev/null; wait $RP 2>/dev/null; RP=; log "rec stopped"; }
# st KEY: one value of the game's state file. The game rewrites the file in place, so a read can catch it half
# written (gate 1907: "realtime 62.10 -> " empty). Only a copy that ends with its "end" line counts; else read again
# (up to 20 times, 0.2 s apart) before giving up with an empty value.
st(){ i=0; while [ $i -lt ${STATE_TRIES:-20} ]; do cp $R/awctl/state.txt $R/state.read 2>/dev/null
    if [ "$(tail -n 1 $R/state.read 2>/dev/null)" = end ]; then
      awk -v k="$1" '$1==k{$1="";sub(/^ /,"");print}' $R/state.read; return 0; fi
    sleep 0.2; i=$((i+1)); done; }
reads(){ grep -o 'reads=[0-9]*' $R/awctl/console.log 2>/dev/null | tail -1 | cut -d= -f2; }
# The engine's efrag safety net keeps the game running; a smoke still fails when it was used (CHIM-FRAME-EDGE-EFRAG-CRASH-36).
# From 32 MB of Fast RAM no CHIM chunk may wait for room in the zone (CHIM-ZONE-BUDGET-33: 0 in Seyda Neen, Balmora and
# Vivec at 32 MB since v0.0.51; at 16 MB the retries are the known cost). ZONEFULL=allow (--allow-zone-full) only counts.
zonefull(){ grep -c "CHIM: .*zone full" $R/awctl/console.log 2>/dev/null; }
# finish RESULT: the first result stands; a finish reached inside $( ) (rc in status/advance) ends only that subshell,
# so the outer script's own finish afterwards must not write a second result over it
# SMOKE-INPLAY-UNSAMPLED-63: every stop is examined (stall.py) before the run ends and before any retry, whichever
# check stopped it; a stop that went through stall() already was examined there ($R/examined).
# SMOKE-IDE-TRACE-LOG-63: the emulator package logs every IDE transfer (compiled in, about a million lines a run);
# the kept logs drop those lines unless IDETRACE=1 (--ide-trace), and say how many went.
idetrim(){ [ "${IDETRACE:-0}" = 1 ] && return 0; for f in "$@"; do [ -f "$f" ] || continue
    n=$(grep -c -E '^IDE[0-9]* ' "$f" 2>/dev/null); grep -v -E '^IDE[0-9]* ' "$f" > "$f.trim" 2>/dev/null; mv "$f.trim" "$f"
    log "ide trace: ${n:-0} lines left out of $(basename $f) (--ide-trace keeps them)"; done; }
finish(){ [ -e $R/finished ] && exit 0; : > $R/finished
  case "$1" in FAIL*) [ -e $R/examined ] || ! alive || { : > $R/examined
      log "examined at the stop: $( (python3 $R/stall.py 5 || echo 'STALL unknown: stall check could not run') 2>/dev/null | tail -n 1)"; };; esac
  [ "${REMOTE:-1}" = 0 ] || case "$1" in PASS*) b=$(st efrags_bad); [ -n "$b" ] && [ "$b" != 0 ] && set -- "FAIL efrag safety net used $b times (console: Efrag safety net)"
    z=$(zonefull); [ "${z:-0}" -gt 0 ] && [ "$FASTMB" -ge 32 ] && [ "${ZONEFULL:-fail}" != allow ] && case "$1" in PASS*)
      if grep -q 'CHIM cache off (skipped for this start)' $R/awctl/console.log 2>/dev/null; then
        set -- "FAIL CHIM zone full $z times at $FASTMB MB of Fast RAM, with the CHIM cache skipped for this start by a key the smoke sent onto the startup logo (SMOKE-M-KEY-SKIPS-CHIM-CACHE-57)"
      else set -- "FAIL CHIM zone full $z times at $FASTMB MB of Fast RAM (none allowed from 32 MB: CHIM-ZONE-BUDGET-33)"; fi;; esac
    [ "$(st screen)" = game ] || set -- "FAIL the run ended outside play: screen $(st screen) (map $(st map))";; esac
  recstop; cp $R/home/Cache/Logs/fs-uae.log.txt $R/logs/fs-uae.log.txt 2>/dev/null
  grep -E "Caught illegal|Fault address|Suspicious" $R/logs/fs-uae.log.txt 2>/dev/null | tail -12 > $R/logs/emulator-faults.txt
  cp $R/awctl/console.log $R/logs/console.log 2>/dev/null; alive && shot final
  kill $FP 2>/dev/null; sleep 2; kill $XP 2>/dev/null; idetrim $R/logs/fs-uae.log.txt $R/logs/fsuae.log
  rm -f $R/home/Cache/Logs/fs-uae.log.txt; log "smoke RESULT $1"; exit 0; }
# emucheck: every --emu-option line must show in the emulator's start-up log (judge.py emucheck), else the run fails:
# a count with an option the emulator never took would prove nothing
emucheck(){ [ -s $R/emu-options.txt ] || return 0
  v=$(python3 $R/judge.py emucheck $R/emu-options.txt $R/home/Cache/Logs/fs-uae.log.txt $R/logs/fsuae.log 2>&1 | tail -n 1); log "$v"
  case "$v" in "EMUOPT ok"*) ;; *) finish "FAIL the emulator did not take its extra options: ${v#EMUOPT }";; esac; }
# play S: S seconds of game time; the emulator must stay up and the game clock must move. A window open (screen not
# "game": inventory, journal, rest, dialogue, ...) whose realtime stood still while the engine's ticks moved is long
# work inside one frame, not a stall (LOAD-STALL-SESSIONS-59); with neither moving it is a stall as before.
play(){ r1=$(st realtime); t1=$(st ticks); s=0
  while [ $s -lt $(($1*K)) ]; do alive || finish "FAIL emulator exited during $2 (map $(st map))"; sleep 1; s=$((s+1)); done
  r2=$(st realtime); t2=$(st ticks); w=$(st screen)
  # SESSION-STALL-AFTER-LONG-FRAME-62: neither realtime nor ticks moved over the wait. The game writes its state file
  # between frames and on the long-work heartbeat only, so one frame of several seconds without a heartbeat (file
  # reads for a script command, a long console print) reads the same as a dead game over a short wait: a session was
  # called stalled 1 s into such a frame. STALL_GRACE seconds (30) for either to move before any verdict; when one
  # does, the frame is logged and the checks below judge the new reading.
  if [ "$t1" = "$t2" ] && { [ -z "$r2" ] || [ "$r1" = "$r2" ]; }; then r3=; t3=; g=0
    while [ $g -lt $((${STALL_GRACE:-30}*K)) ]; do alive || finish "FAIL emulator exited during $2 (map $(st map))"
      sleep 1; g=$((g+1)); r3=$(st realtime); t3=$(st ticks)
      [ -n "$r3" ] && { [ "$r3" != "$r1" ] || [ "$t3" != "$t1" ]; } && break; done
    [ -n "$r3" ] && { [ "$r3" != "$r1" ] || [ "$t3" != "$t1" ]; } && { log "long frame during $2: realtime $r1 and ticks $t1 stood for $1 s and $g s more, then went on (realtime $r3, ticks $t3)"; r2=$r3; t2=$t3; w=$(st screen); }; fi
  [ -n "$r2" ] && [ "$r1" = "$r2" ] && [ -n "$t2" ] && [ "$t1" != "$t2" ] && [ -n "$w" ] && [ "$w" != game ] &&
    { log "window $w during $2: realtime $r1 -> $r2, ticks $t1 -> $t2 (the engine runs)"; return 0; }
  # ARRIVAL-LONG-FRAME-DEV6-59: realtime standing on the game screen while the ticks move is long work inside one
  # frame (the engine's busy heartbeat), not a disk stall: it gets BUSY_GRACE seconds (60) for the frame to end and is
  # named "long frame (busy)"; a stop with the ticks standing too goes on to the stall examination below as before
  if [ -n "$r2" ] && [ "$r1" = "$r2" ] && [ -n "$t2" ] && [ "$t1" != "$t2" ]; then g=0
    while [ $g -lt $((${BUSY_GRACE:-60}*K)) ] && [ "$(st realtime)" = "$r1" ]; do alive || finish "FAIL emulator exited during a long frame in $2"; sleep 1; g=$((g+1)); done
    r2=$(st realtime)
    [ -n "$r2" ] && [ "$r2" != "$r1" ] && { log "long frame (busy) during $2: realtime stood at $r1 for $1 s and $g s more while the engine ran (ticks $t1 -> $t2)"; return 0; }
    finish "FAIL long frame (busy) during $2: realtime stood at $r1 for $1 s and ${BUSY_GRACE:-60} s more while the engine ran (ticks $t1 -> $t2), not a disk stall"; fi
  [ -n "$r2" ] && [ "$r1" != "$r2" ] || finish "FAIL game stalled during $2 (realtime $r1 -> $r2)"; }
# inplay WHAT: the map is in play, not only loaded under a menu (SMOKE-PASSES-WITHOUT-MAP-36): within 30 s the
# client has its world (signon 4, world leaves) and the screen is the game. An engine without these state lines fails.
inplay(){ s=0; while [ $s -lt $((30*K)) ]; do alive || finish "FAIL emulator exited before $1 was in play"
    [ "$(st screen)" = game ] && [ "$(st signon)" = 4 ] && [ "$(st world_leafs)" -gt 0 ] 2>/dev/null && { log "in play: $1 (map $(st map), $(st world_leafs) leaves, local $(st local))"; return 0; }
    sleep 1; s=$((s+1)); done
  # SMOKE-INPLAY-UNSAMPLED-63: examined like a load that never finished (gate 9950's stop was not sampled)
  stall "$1 is not in play: screen $(st screen), signon $(st signon), world leaves $(st world_leafs) (map $(st map))"; }
# stall: a load that does not finish is examined with the FS-UAE monitor (stall.py): an emulator disk stall (the
# processor idle, the game's file request taken by a handler and never answered, CHIM-SEYDA-BALMORA-LOAD-HANG-43)
# is named as such; the launcher retries such a run once on a fresh play copy.
stall(){ : > $R/examined; S=$( (python3 $R/stall.py 5 || echo 'STALL unknown: stall check could not run') 2>/dev/null | tail -n 1); log "$S"
  case "$S" in "STALL emulator-disk"*) finish "FAIL emulator disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43) $1: ${S#STALL emulator-disk: }";;
    "STALL busy"*) finish "FAIL long frame (busy) $1: ${S#STALL busy: }";; esac
  finish "FAIL $1 ($S)"; }
# loaded SERVER: wait (max 150 s) for the map to run
loaded(){ s=0; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited loading $1";
  [ "$(st server)" = "$1" ] && return 0; sleep 1; s=$((s+1)); done; stall "$1 did not load (server $(st server))"; }
t0=$(date +%s)
sleep $((9*K))
# ROUTE-OFF-BEGIN
# REMOTE=0 (experiment E2, CHIM-SEYDA-BALMORA-LOAD-HANG-43): no remote console, nothing typed. The play copy's
# autoexec turns the debug HUD on and runs the route itself (map MAP1, then dbg tp TP and map MAP1 in turn, a fixed
# number of frames apart). A screenshot every SHOTEVERY s for ROUTESECS s; each is kept with its SHA-256 in
# frames.txt. The HUD clock and frame counter change every few seconds in play, so the same picture for FROZEN s
# (150, the smoke's own load limit) is a frozen clock: a stop, examined like any other (stall.py) and failed.
if [ "${REMOTE:-1}" = 0 ]; then
  log "remote console off: the route runs from the play copy's autoexec; a screenshot every ${SHOTEVERY:-10} s for ${ROUTESECS:-600} s, a stop = the same picture for ${FROZEN:-150} s"
  : > $R/frames.txt; i=0; until_t=$(( $(date +%s) + ${ROUTESECS:-600}*K ))
  while [ $(date +%s) -lt $until_t ]; do alive || finish "FAIL emulator exited on the route, remote console off ($(( $(date +%s) - t0 )) s)"
    i=$((i+1)); f=$(printf 'route-%03d' $i); shot $f
    [ -s $R/shots/$f.png ] && echo "$(( $(date +%s) - t0 )) $(sha256sum $R/shots/$f.png | cut -c1-64) $f" >> $R/frames.txt
    [ $i = 1 ] && emucheck
    v=$(python3 $R/judge.py live $R/frames.txt ${FROZEN:-150} 2>&1 | tail -n 1)
    case "$v" in STOP*) stall "frozen clock on the route, remote console off: ${v#STOP }";; esac
    sleep $((${SHOTEVERY:-10}*K)); done
  v=$(python3 $R/judge.py final $R/frames.txt ${FROZEN:-150} 2>&1 | tail -n 1)
  case "$v" in PASS*) finish "PASS remote console off, route ${v#PASS }";; STOP*) stall "frozen clock on the route, remote console off: ${v#STOP }";;
    *) finish "FAIL remote console off, route ${v#* }";; esac
fi
# ROUTE-OFF-END
# BOOT-WAIT-BEGIN
n=0; while [ ! -s $R/awctl/state.txt ] && [ $n -lt $((${BOOT_WAIT:-300}*K)) ]; do
  # Escape first: the start-up logo takes every key, and its memory notice reads M as "not now" (the CHIM cache off
  # for this start): the m of "aw_remote" typed onto the logo failed gate smokes with the zone full
  # (SMOKE-M-KEY-SKIPS-CHIM-CACHE-57). Escape ends the logo before anything is typed.
  # PERSISTING 2026-11-03: on a busy host the game was still loading when that Escape came, the logo started after it
  # and the typed m still skipped the cache (gates 5916, 6201, 6202, 6222, 6262: "remote up after 21-22 s"). The play
  # copy's id1/autoexec.cfg already turns the remote on, so the smoke now only presses Escape while it waits, and types
  # "aw_remote 1" only as a late fallback, after 90 s, when any logo is long gone.
  # REGRESSION 2026-11-04 (gate 6418, a from-scratch build on all cores): the logo came after 90 s and the late
  # fallback's m skipped the cache again. No timing is safe, so the smoke types NOTHING before the game's own remote
  # answers: the play copy's id1/autoexec.cfg turns the remote on, and the remote's state file is the ready signal.
  # No key at all while waiting: gate 6810 showed that an Escape sent before the game runs lands in the AmigaDOS
  # window's start-up preflight ("Starting in 2 s...") as typed input and holds it there, so the game never starts.
  # BOOT_WAIT (300 s) bounds the wait; no remote by then fails as "no remote control", never by typing onto the screen.
  alive || finish "FAIL emulator exited during boot"
  sleep $((2*K)); n=$((n+2*K)); done
# BOOT-WAIT-END
# The game runs now (its remote answers): Escape ends a start-up logo that is still up or comes later; Escape never
# answers the logo's memory notice (only M does), so it is safe at any time after this point.
# remote_up: the game rewrites state.txt in place, so one look can catch it empty mid-write; a gate smoke failed
# "no remote control after boot" 15 s in, twice in a row, with the remote already up (GATE-SMOKE-NO-REMOTE-CONTROL-60,
# 2026-11-05). Look up to 10 times, 0.5 s apart, as st() does, before calling the remote absent.
remote_up(){ i=0; while [ $i -lt 10 ]; do [ -s $R/awctl/state.txt ] && return 0; sleep 0.5; i=$((i+1)); done; return 1; }
remote_up && for i in 1 2 3; do key Escape; sleep $((2*K)); done
remote_up || finish "FAIL no remote control after boot ($(( $(date +%s) - t0 )) s; the play copy's autoexec turns it on, nothing is typed before it answers)"
log "boot: remote up after $(( $(date +%s) - t0 )) s"; shot menu; emucheck
if [ "${START:-map}" = enter ] || [ "${START:-map}" = auto ]; then  # a MiniWind image starts its own scene; Enter through its quick character pages
  [ "${START:-map}" = auto ] || key Return
  # MAP1 any: the map the image starts on, whichever it is (a MiniWind holds one; TEST-HARNESS-MINIWIND-62: a session
  # that named another map waited for it and stopped on the character name page)
  if [ "$MAP1" = any ]; then s=0; v=; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited loading the image's start map"
      v=$(st server); [ -n "$v" ] && [ "$v" != none ] && break; sleep 1; s=$((s+1)); done
    [ -n "$v" ] && [ "$v" != none ] || stall "the image's start map did not load (server $(st server))"; MAP1=$v; log "start map from the game: $MAP1"; fi
  loaded "$MAP1"; i=0  # until the view renders (local origin not 0 0 0), at most 20 pages
  while [ "${START:-map}" != auto ] && [ $i -lt 20 ] && { [ "$(st map)" = none ] || [ "$(st local)" = "0 0 0" ]; }; do sleep $((2*K)); key Return; i=$((i+1)); done
  sleep $((2*K)); [ "$(st map)" != none ] && [ "$(st local)" != "0 0 0" ] || finish "FAIL $MAP1 runs but the game never started (client map $(st map))"
  log "in game after $i Enter presses: local $(st local)"
else rc "map $MAP1"; loaded "$MAP1"; case "$AFTER" in key:*) sleep $((3*K)); key "${AFTER#key:}"; log "after load: key ${AFTER#key:}";; ?*) rc "$AFTER"; log "after load: $AFTER";; esac; fi
inplay "$MAP1"
play $PLAY "$MAP1 (music on)"; shot map1
# SWEEP (ENTITY-SWEEP-AB): dbg sweep on the loaded area, its SWEEP RESULT line logged with the time it took; fail = a
# FAIL result (or no result) fails the smoke; report (default) only logs it; off skips it
if [ "${SWEEP:-report}" != off ]; then
  rc "aw_sweep"; sleep $((4*K)); sw=$(grep -o 'SWEEP RESULT.*' $R/awctl/console.log 2>/dev/null | tail -1)
  log "sweep: ${sw:-no SWEEP RESULT line}"
  [ "${SWEEP:-report}" = fail ] && { case "$sw" in *"RESULT ok"*) ;; *) finish "FAIL dbg sweep: ${sw:-no result line}";; esac; }
fi
# SCRIPT: a scripted session instead of the music and second-load steps (evidence shots, replays). One step per line:
# "cmd TEXT" console command, "key NAME" key press, "xdo ARGS" raw xdotool steps (mouse, held keys), "wait S" S seconds of game time (the game must keep running),
# "shot NAME" screenshot shots/NAME.png, "rec NAME" starts the clip shots/NAME.mp4, "recstop" ends it,
# "state KEY" logs that state value; other lines are comments. Ends PASS
# when the game survives the whole script.
if [ -s $R/script.txt ]; then
  while IFS= read -r line <&3 || [ -n "$line" ]; do  # fd 3: ffmpeg (shot) reads stdin
    case "$line" in
    cmd\ *) rc "${line#cmd }";;
    key\ *) key "${line#key }"; log "key ${line#key }";;
    xdo\ *) xdo "${line#xdo }"; log "xdo ${line#xdo }";;
    wait\ *) play "${line#wait }" "script ($(st map))";;
    shot\ *) shot "${line#shot }"; log "shot ${line#shot } at local $(st local)";;
    rec\ *) rec "${line#rec }";;
    recstop) recstop;;
    state\ *) log "state ${line#state }: $(st ${line#state })";;
    esac
    alive || finish "FAIL emulator exited after script step: $line"
  done 3< $R/script.txt
  [ "$(st screen)" = game ] && [ "$(st signon)" = 4 ] && [ "$(st world_leafs)" -gt 0 ] 2>/dev/null ||
    finish "FAIL scripted run ended outside play: map $(st map), signon $(st signon), world leaves $(st world_leafs)"
  finish "PASS script, $(st map) running, $(( $(date +%s) - t0 )) s"
fi
a=$(status); [ -n "$a" ] || stall "no answer to aw_music_status in $MAP1"
sleep $((5*K)); b=$(advance "$a")
[ -n "$a" ] && [ -n "$b" ] && [ "$b" -gt "$a" ] || finish "FAIL music not reading in $MAP1 (reads $a -> $b over ${MUSIC_WAIT:-45} s)"
log "music on: reads $a -> $b"
rc "aw_music_status off"; sleep $((3*K)); grep -q "Background music off" $R/awctl/console.log || finish "FAIL dbg music off not confirmed"
play 5 "music off"; e=$(status); [ -n "$e" ] || stall "no answer to aw_music_status with the music off"
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
[ $s -lt $((150*K)) ] || stall "map ${TP#map:} did not load a map (server $(st server))";;
*)
# REPEAT: the map change runs REPEAT times (back to MAP1 with "map MAP1" in between), so an intermittent hang
# fails the smoke instead of passing on a lucky run (CHIM-SEYDA-BALMORA-LOAD-HANG-43).
r=1; while :; do
rc "dbg tp $TP"; s=0; while [ $s -lt $((150*K)) ]; do alive || finish "FAIL emulator exited after dbg tp $TP (load $r of $REPEAT)";
  [ "$(st server)" != "$MAP1" ] && [ -n "$(st server)" ] && [ "$(st server)" != none ] && break; sleep 1; s=$((s+1)); done
[ $s -lt $((150*K)) ] || stall "dbg tp $TP did not load a map (server $(st server), load $r of $REPEAT)"
[ $r -ge $REPEAT ] && break
inplay "the second load ($(st server), load $r of $REPEAT)"; sleep $((3*K)); r=$((r+1))
rc "map $MAP1"; loaded "$MAP1"; inplay "$MAP1 again (before load $r of $REPEAT)"; sleep $((3*K))
done; log "map change ran $r times";;
esac
inplay "the second load ($(st server))"
play $PLAY "$(st server) (music off)"; shot map2
c=$(status); [ -n "$c" ] || stall "no answer to aw_music_status after the second load"
[ "$c" = "$e" ] || finish "FAIL music read while off (reads $e -> $c)"
rc "aw_music_status on"; sleep $((3*K)); d=$(advance "$c")
[ -n "$d" ] && [ "$d" -gt "${c:-0}" ] || finish "FAIL music did not read again after dbg music on (reads $c -> $d over ${MUSIC_WAIT:-45} s)"
play 5 "music on again"
finish "PASS boot, $MAP1 and $(st server) loaded, music reads $a -> $b, off (reads stayed $c), on again ($c -> $d), $(( $(date +%s) - t0 )) s"
'''


# The emulator side of a stalled load (CHIM-SEYDA-BALMORA-LOAD-HANG-43), written to OUT/stall.py and run by PROBE's
# stall step with the FS-UAE monitor on: break in (Alt+D), sample the program counter once a second, walk exec's
# task lists and look for the file-system request the game waits on. One line on stdout:
# "STALL <class>: <details>"; class "emulator-disk" = every sample in Kickstart's idle loop (STOP) and the game
# process waiting on SIGF_DOS with its request taken by a file-system handler that never answered.
STALL_PY = r'''#!/usr/bin/env python3
import os, re, subprocess, sys, time
R = '/out'
LOG = R + '/logs/fsuae.log'
FIFO = R + '/dbg.in'
IDLE = (0xF81460, 0xF81480)     # Kickstart 3.1 exec idle loop (STOP)
PROMPT = re.compile(r'(?:^|\r?\n)>[ \t]*$')


def tail_from(pos):
    with open(LOG, 'rb') as f:
        f.seek(pos)
        return f.read().decode('latin-1', 'replace')


def size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def wait_prompt(pos, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        text = tail_from(pos)
        if PROMPT.search(text.rstrip(' \t')):
            return text
        time.sleep(0.15)
    return None


def cmd(text, timeout=20):
    pos = size()
    with open(FIFO, 'w') as f:
        f.write(text + '\n')
    return wait_prompt(pos, timeout) or ''


def break_in():
    w = subprocess.run(['xdotool', 'search', '--name', 'FS-UAE'], capture_output=True, text=True).stdout.split()
    if not w:
        return False
    pos = size()
    for a in (['windowfocus', '--sync', w[0]], ['keydown', 'Alt_L'], ['key', '--delay', '150', 'd'], ['keyup', 'Alt_L']):
        subprocess.run(['xdotool'] + a, capture_output=True)
    return wait_prompt(pos) is not None


def resume():
    with open(FIFO, 'w') as f:
        f.write('g\n')


def mread(addr, n):
    out = bytearray()
    for line in cmd('m $%08X !%d' % (addr, (n + 15) // 16)).splitlines():
        parts = line.split()
        if not parts or not re.fullmatch(r'[0-9A-Fa-f]{8}', parts[0]):
            continue
        for p in parts[1:]:
            if not re.fullmatch(r'[0-9A-Fa-f]{4}', p):
                break
            out += bytes.fromhex(p)
    return bytes(out[:n])


def be32(b, o):
    return int.from_bytes(b[o:o + 4], 'big') if len(b) >= o + 4 else 0


ACTIONS = {8: 'LOCATE_OBJECT', 15: 'FREE_LOCK', 16: 'DELETE_OBJECT', 23: 'EXAMINE_OBJECT', 24: 'EXAMINE_NEXT',
           29: 'PARENT', 82: 'READ', 87: 'WRITE', 1004: 'FINDUPDATE', 1005: 'FINDINPUT', 1006: 'FINDOUTPUT',
           1007: 'END', 1008: 'SEEK', 1022: 'SET_FILE_SIZE', 1027: 'IS_FILESYSTEM'}


def pending(game, queues):
    """SMOKE-INPLAY-UNSAMPLED-63 / SMOKE-STALL-LABEL-INFERRED-60: the game's file request read from the ports, not
    inferred from its stack. game: the game task tuple (node at [1]); queues: {port owner name: [(packet, dp_Port,
    dp_Type, dp_Arg1)]}, the game's own reply port under 'Initial CLI'. Returns (handler or None, text)."""
    if not game:
        return None, 'game task not found'
    reply = game[1] + 0x5C
    back = [q for q in queues.get('Initial CLI', [])]
    if back:
        p = back[0]
        return 'Initial CLI', 'the reply to %s (arg1 $%08X) is on the game\'s port but the game still waits: ' \
            'the completion signal was lost' % (ACTIONS.get(p[2], 'type %d' % p[2]), p[3])
    for name, msgs in sorted(queues.items()):
        for p in msgs:
            if name != 'Initial CLI' and p[1] == reply:
                return name, 'request %s (arg1 $%08X, packet $%08X) queued on %s\'s port, not taken' % (
                    ACTIONS.get(p[2], 'type %d' % p[2]), p[3], p[0], name)
    return None, 'no request of the game queued on any handler port (taken by a handler, or the call is not a file call)'


def classify(pcs, tasks, stack, queues=None):
    """pcs: sampled program counters; tasks: [(name, node, sigwait, is_process)]; stack: the game's stack words;
    queues: the message ports read (see pending), None when they could not be read. Returns (class, details)."""
    idle = [p for p in pcs if IDLE[0] <= p < IDLE[1]]
    game = next((t for t in tasks if t[0] == 'Initial CLI'), None)
    lists = {t[1] + 0x5C + 0x14: t[0] for t in tasks if t[3] and t[0] != 'Initial CLI'}
    holder = next((lists[w] for w in stack if w in lists), None)
    named, text = pending(game, queues) if queues is not None else (None, 'ports not read')
    details = 'pc %d of %d samples in exec idle; game %s; pending: %s; stack scan (inferred): request held by %s' % (
        len(idle), len(pcs), 'waits on SIGF_DOS' if game and game[2] & 0x100 else 'not in a file call', text,
        holder or 'none found')
    if pcs and len(idle) == len(pcs) and game and game[2] & 0x100 and (holder or named):
        return 'emulator-disk', details
    # ARRIVAL-LONG-FRAME-DEV6-59: three samples or more and none in exec idle: the processor is working (a long run of
    # file and game work inside one frame), not a request nobody answers
    if len(pcs) >= 3 and not idle:
        return 'busy', details
    return 'unknown', details


LT_OPS = {1: 'open', 2: 'read', 3: 'seek', 4: 'close'}
LT_HEADER, LT_ENTRY = 24, 64


def ring_lines(raw):
    """LOAD-HANG-WATCHDOG-62: the engine's load trace ring (aw_loadtrace.c layout) read from memory -> (lines oldest
    first, the unfinished calls). Header: AWLTRACE, count, entries, entry size, started; entry: t0, t1 (0xFFFFFFFF
    not finished), bytes, result, op, stage[11], name[36]."""
    if len(raw) < LT_HEADER or raw[:8] != b'AWLTRACE':
        return [], []
    count, entries, size = be32(raw, 8), be32(raw, 12), be32(raw, 16)
    if size != LT_ENTRY or not 0 < entries <= 1024:
        return [], []
    lines, open_ = [], []
    for seq in range(max(1, count - entries + 1), count + 1):
        o = LT_HEADER + ((seq - 1) % entries) * LT_ENTRY
        e = raw[o:o + LT_ENTRY]
        if len(e) < LT_ENTRY:
            break
        t0, t1, nbytes, result = be32(e, 0), be32(e, 4), be32(e, 8), be32(e, 12)
        nbytes -= (nbytes >> 31) << 32
        result -= (result >> 31) << 32
        stage = e[17:28].split(b'\x00')[0].decode('latin-1', 'replace')
        name = e[28:64].split(b'\x00')[0].decode('latin-1', 'replace')
        head = 'LT %d %s %s %s %d bytes' % (seq, stage, LT_OPS.get(e[16], '?'), name, nbytes)
        if t1 == 0xFFFFFFFF:
            lines.append('%s, at %d ms, NOT FINISHED' % (head, t0))
            open_.append(lines[-1])
        else:
            lines.append('%s -> %d, at %d ms, %d ms' % (head, result, t0, (t1 - t0) & 0xFFFFFFFF))
    return lines, open_


def load_trace():
    """The ring named by the console's last "Load trace on: ring at $ADDR" line, read with the monitor (the game is
    stopped); its lines go to logs/loadtrace-at-stop.txt. Returns the summary for the STALL line ('' when off)."""
    if os.environ.get('LOADTRACE') != '1':
        return ''
    try:
        text = open(R + '/awctl/console.log', encoding='latin-1').read()
    except OSError:
        text = ''
    found = re.findall(r'Load trace on: ring at \$([0-9A-Fa-f]{8})', text)
    if not found:
        return '; load trace: no ring address on the console'
    raw = mread(int(found[-1], 16), LT_HEADER + 128 * LT_ENTRY)
    lines, open_ = ring_lines(raw)
    with open(R + '/logs/loadtrace-at-stop.txt', 'w') as f:
        f.write('\n'.join(lines) + '\n')
    if not lines:
        return '; load trace: ring at $%s not readable' % found[-1]
    return '; load trace: %d calls kept, last %s; not finished: %s' % (
        len(lines), lines[-1], ' | '.join(open_[-3:]) or 'none')


def main():
    pcs = []
    for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 5):
        if not break_in():
            continue
        m = re.search(r'^([0-9A-Fa-f]{8}) ', cmd('d').strip(), re.M)
        if m:
            pcs.append(int(m.group(1), 16))
        resume(); time.sleep(1)
    tasks, stack = [], []
    if break_in():
        eb = be32(mread(4, 4), 0)
        base = mread(eb, 0x1B0)
        for off in (0x196, 0x1A4):
            node, k = be32(base, off), 0
            while node and k < 40:
                t = mread(node, 0x60)
                if not be32(t, 0):
                    break
                np = be32(t, 10)
                name = mread(np, 32).split(b'\x00')[0].decode('latin-1', 'replace') if np else ''
                tasks.append((name, node, be32(t, 22), len(t) > 8 and t[8] == 13))
                if name == 'Initial CLI':
                    s = mread(be32(t, 54) & ~1, 3072)
                    stack = [be32(s, i) for i in range(0, len(s) - 3, 2)]
                node, k = be32(t, 0), k + 1
        # every process's message port (pr_MsgPort at +0x5C, its list at +0x14): the packets queued there
        queues = {}
        for name, node, _sig, proc in tasks:
            if not proc:
                continue
            lst = node + 0x5C + 0x14
            msg, k, got = be32(mread(lst, 4), 0), 0, []
            while msg and msg != lst + 4 and k < 8:
                m = mread(msg, 14)
                pk = be32(m, 10)          # mn_Node.ln_Name = the DosPacket of a StandardPacket
                if pk:
                    d = mread(pk, 24)
                    got.append((pk, be32(d, 4), be32(d, 8), be32(d, 20)))
                msg, k = be32(m, 0), k + 1
            if got:
                queues[name] = got
        trace = load_trace()      # LOAD-HANG-WATCHDOG-62: the last file calls, read while the game is stopped
        resume()
    else:
        queues, trace = None, ''
    kind, details = classify(pcs, tasks, stack, queues)
    print('STALL %s: %s; pc %s%s' % (kind, details, ' '.join('%08X' % p for p in pcs[:5]), trace))


if __name__ == '__main__':
    main()
'''


# The emulator side's judge (OUT/judge.py, run with python3 in the FS-UAE container), experiments E2 and E3 of
# CHIM-SEYDA-BALMORA-LOAD-HANG-43. Standard library only; the same functions are loaded here for the unit tests.
#   judge.py live|final FRAMES FROZEN: FRAMES = lines "SECONDS SHA256 NAME" (one per screenshot). A stop = the same
#     picture (debug HUD clock and frame counter included) over FROZEN seconds or more. live: only the newest run of
#     equal pictures counts; final: any run, and a route that never moved fails. One line: "STOP ...", "PASS ...",
#     "RUN ..." (live, nothing yet) or "FAIL ...".
#   judge.py emucheck OPTIONS LOG...: every "key = value" line of OPTIONS must show in one of the logs. One line:
#     "EMUOPT ok ..." or "EMUOPT missing ...".
JUDGE_PY = r'''#!/usr/bin/env python3
import re, sys

# what the emulator writes when it took an option (FS-UAE 3.1.66 source: od-fs/libamiga.cpp
# amiga_set_deterministic_mode); any other key must appear as "key = value" in a log
EMU_PROOF = {'deterministic': ('1', 'libamiga enabling net play mode')}


def judge_frames(frames, frozen, final=False, min_distinct=3):
    """frames: [(seconds, digest)] in time order. Returns (verdict, details)."""
    if not frames:
        return ('FAIL' if final else 'RUN'), 'no screenshot taken'
    runs, start = [], 0
    for i in range(1, len(frames) + 1):
        if i == len(frames) or frames[i][1] != frames[start][1]:
            runs.append((frames[start][0], frames[i - 1][0], i - start))
            start = i
    longest = max(runs, key=lambda r: r[1] - r[0])
    look = runs if final else runs[-1:]
    for t0, t1, n in look:
        if t1 - t0 >= frozen:
            return 'STOP', 'the same picture from %d s to %d s (%d shots, %d s; limit %d s)' % (t0, t1, n, t1 - t0, frozen)
    distinct = len(set(d for _t, d in frames))
    summary = '%d shots over %d s, %d different pictures, longest still %d s' % (
        len(frames), frames[-1][0] - frames[0][0], distinct, longest[1] - longest[0])
    if not final:
        return 'RUN', summary
    if distinct < min_distinct:
        return 'FAIL', 'the picture hardly moved: ' + summary
    return 'PASS', summary


def read_frames(path):
    out = []
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.split()
        if len(p) >= 2 and p[0].isdigit():
            out.append((int(p[0]), p[1]))
    return out


def emu_check(options, logs):
    """options: [(key, value)]; logs: the emulator's log texts. Returns the keys not shown as taken."""
    text = '\n'.join(logs)
    missing = []
    for key, value in options:
        proof = EMU_PROOF.get(key)
        if proof and proof[0] == value:
            ok = proof[1] in text
        else:
            ok = re.search(r'(?m)\b%s\s*=\s*%s\s*$' % (re.escape(key), re.escape(value)), text) is not None
        if not ok:
            missing.append('%s=%s' % (key, value))
    return missing


def main(argv):
    if argv[0] in ('live', 'final'):
        verdict, details = judge_frames(read_frames(argv[1]), int(argv[2]), final=argv[0] == 'final')
        print('%s %s' % (verdict, details))
        return 0
    if argv[0] == 'emucheck':
        opts = []
        for line in open(argv[1], encoding='utf-8'):
            if '=' in line:
                k, v = line.split('=', 1)
                opts.append((k.strip(), v.strip()))
        logs = []
        for p in argv[2:]:
            try:
                logs.append(open(p, encoding='utf-8', errors='replace').read())
            except OSError:
                pass
        missing = emu_check(opts, logs)
        print('EMUOPT missing %s (not in the emulator log)' % ', '.join(missing) if missing
              else 'EMUOPT ok %s taken (emulator log)' % ', '.join('%s=%s' % o for o in opts))
        return 0
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
'''
_JUDGE = {'__name__': 'judge'}
exec(compile(JUDGE_PY, 'judge.py', 'exec'), _JUDGE)
judge_frames = _JUDGE['judge_frames']
emu_check = _JUDGE['emu_check']

# Keys the smoke sets itself: an --emu-option may not change the machine under test (memory, disks, ROM, CPU,
# the JIT profile, the monitor the stall check needs, the screenshot paths)
EMU_MANAGED = re.compile(r'^(amiga_model|cpu|fpu|uae_cpu_24bit_addressing|chip_memory|slow_memory|fast_memory|'
                         r'zorro_iii_memory|kickstart_file|hard_drive_.*|floppy_.*|joystick_port_.*|fullscreen|'
                         r'window_.*|console_debugger|screenshots_output_dir|base_dir|jit_compiler|uae_cpu_speed)$')


def parse_emu_options(items):
    """--emu-option KEY=VALUE values -> [(key, value)]; raises ValueError on a bad or a managed key. ['none'] = []."""
    if list(items) == ['none']:
        return []
    out = []
    for item in items:
        key, sep, value = item.partition('=')
        key, value = key.strip(), value.strip()
        if not sep or not re.fullmatch(r'[a-z][a-z0-9_]*', key) or not re.fullmatch(r'[A-Za-z0-9_.:/+-]+', value):
            raise ValueError('emulator option %r: KEY=VALUE, a lower-case key and a plain value' % item)
        if EMU_MANAGED.match(key):
            raise ValueError('emulator option %r: the smoke sets %s itself' % (item, key))
        out.append((key, value))
    return out


def emu_config_lines(options):
    """The lines appended to the emulator config (OUT/emu-options.txt)."""
    return ''.join('%s = %s\n' % kv for kv in options)


ROUTE_WAIT_CHUNK = 50


def route_autoexec(map1, tp, frames, load_trace=False):
    """The play copy's id1/autoexec.cfg for --remote off (experiment E2): debug HUD on (its clock is what the
    screenshots are judged by), then map MAP1 and dbg tp TP in turn, FRAMES frames apart, until the run ends."""
    if not re.fullmatch(r'[a-z0-9_]+', map1):
        raise ValueError('route map %r: a plain map name' % map1)
    if not re.fullmatch(r'-?\d+ -?\d+', tp):
        raise ValueError('route teleport %r: "X Y" (dbg tp)' % tp)
    if frames < 1:
        raise ValueError('route frames must be 1 or more')
    chunks = -(-frames // ROUTE_WAIT_CHUNK)
    lines = ['dbg all on', 'dbg coords on'] + (['aw_loadtrace 1'] if load_trace else []) + [
        'alias aw_e2w "%s"' % ';'.join(['wait'] * ROUTE_WAIT_CHUNK),
        'alias aw_e2p "%s"' % ';'.join(['aw_e2w'] * chunks),
        'alias aw_e2b "dbg tp %s;aw_e2p;aw_e2s"' % tp,
        'alias aw_e2s "map %s;aw_e2p;aw_e2b"' % map1,
        'aw_e2s']
    return '\n'.join(lines) + '\n'


def count_class(result):
    """A run's result line -> pass / stop / fail, for the alternating counts."""
    if result.startswith('PASS'):
        return 'pass'
    if re.search(r'emulator disk stall|frozen clock|stopped taking commands|is not in play|did not load|'
                 r'game stalled|no answer to aw_music_status', result):
        return 'stop'
    return 'fail'


def strip_options(argv, names):
    """argv without the options in NAMES (each with its value)."""
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in names:
            skip = True
            continue
        if any(a.startswith(n + '=') for n in names):
            continue
        out.append(a)
    return out


def alternate(args, argv):
    """--alternate remote|emu --runs N: N rounds of the two variants in turn, each its own smoke (no retry), and
    the counts. remote: remote console on, then off. emu: remote on without, then with the --emu-option lines."""
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = strip_options(argv, ('--alternate', '--runs', '--out', '--remote', '--name')) + ['--no-stall-retry']
    if args.alternate == 'remote':
        emu = []      # any --emu-option stays in base: both variants get it
        variants = [('remote-on', ['--remote', 'on']), ('remote-off', ['--remote', 'off'])]
    else:
        base = strip_options(base, ('--emu-option',))
        emu = []
        variants = [('plain', ['--remote', 'on', '--emu-option', 'none']),
                    ('emu', ['--remote', 'on'] + [x for o in args.emu_option for x in ('--emu-option', o)])]
    counts = {name: {'pass': 0, 'stop': 0, 'fail': 0} for name, _ in variants}
    table = out / 'counts.tsv'
    with open(table, 'a', encoding='utf-8', newline='\n') as f:
        f.write('# round\tvariant\tclass\tresult (%s)\n' % ' '.join(argv))
    for i in range(1, args.runs + 1):
        for name, extra in variants:
            sub = out / ('%02d-%s' % (i, name))
            print('=== ROUND %d/%d: %s ===' % (i, args.runs, name), flush=True)
            code = main(base + emu + extra + ['--out', str(sub), '--name', '%s-%s' % (args.name, name)])
            steps = sub / 'logs' / 'steps.log'
            lines = steps.read_text(encoding='utf-8', errors='replace').splitlines() if steps.is_file() else []
            result = next((l.split('smoke RESULT ', 1)[1] for l in reversed(lines) if 'smoke RESULT ' in l),
                          'FAIL no result line (exit %d)' % code)
            kind = count_class(result)
            counts[name][kind] += 1
            with open(table, 'a', encoding='utf-8', newline='\n') as f:
                f.write('%d\t%s\t%s\t%s\n' % (i, name, kind, result))
            print('round %d %s: %s: %s' % (i, name, kind, result), flush=True)
    line = 'COUNTS ' + '; '.join('%s: %d pass, %d stop, %d other fail of %d' % (
        n, c['pass'], c['stop'], c['fail'], args.runs) for n, c in counts.items())
    with open(table, 'a', encoding='utf-8', newline='\n') as f:
        f.write('# %s\n' % line)
    print(line)
    print('smoke-exit=0')
    return 0


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
    ap.add_argument('--fast-mb', type=int, default=DEFAULT_FAST_MB, choices=(16, 32, 64, 128, 256, 512, 1024),
                    help='Zorro III Fast RAM in MiB (default 32: the game needs 32 MB of Fast RAM since 27 October '
                    '2026, the maintainer\'s order; 16 only to look at the old baseline; 128 = what a playtest starts with)')
    ap.add_argument('--map', default='seyda', help='the first map; with --start enter, "any" takes the map the image '
                    'starts on (a MiniWind holds one)')
    ap.add_argument('--tp', default='-21800 -12300',
                    help='second load as dbg tp X Y (default Balmora); "same X Y" for a one-area image: teleport inside --map; '
                         '"view X Y Z": noclip + aw_view to a local point of --map, checked on the client; map:NAME: a second map the image holds')
    ap.add_argument('--play', type=int, default=10)
    ap.add_argument('--no-stall-retry', action='store_true',
                    help='fail at once on an emulator disk stall instead of retrying the run once (used by the retry itself)')
    ap.add_argument('--allow-zone-full', action='store_true',
                    help='from 32 MB a CHIM "zone full" retry fails the smoke (CHIM-ZONE-BUDGET-33); with this it is '
                    'only counted (diagnostic runs)')
    ap.add_argument('--repeat', type=int, default=3,
                    help='run the --tp map change this many times (back to --map in between), so an intermittent load hang '
                         'fails the smoke (CHIM-SEYDA-BALMORA-LOAD-HANG-43); default 3')
    ap.add_argument('--after-load', default='', help='sent once the first map is loaded: a console command, or key:NAME for a key press, '
                    'e.g. key:Return for a MiniWind image, which holds its startup screen until Enter')
    ap.add_argument('--log-illegal', action='store_true',
                    help='FS-UAE logs the 68k PC of every unmapped memory access (uae_log_illegal_mem; with --prof interp)')
    ap.add_argument('--ide-trace', action='store_true',
                    help='keep the emulator\'s IDE transfer trace in the saved logs (about a million lines a run; '
                         'left out by default: SMOKE-IDE-TRACE-LOG-63); for a disk investigation')
    ap.add_argument('--load-trace', action='store_true', default=os.environ.get('AW_SMOKE_LOAD_TRACE') == '1',
                    help='turn the engine\'s load trace on in the play copy (aw_loadtrace 1; off by default, also '
                         'AW_SMOKE_LOAD_TRACE=1): every file call kept in memory, dumped to the console at each Scene '
                         'ready, and read from memory by the examination of a stop (logs/loadtrace-at-stop.txt)')
    ap.add_argument('--start', choices=('map', 'enter', 'auto'), default='map',
                    help='map: load --map from the console (default); enter: press Enter on a MiniWind startup screen, which starts '
                         'its own scene (--map names the map it must load)')
    ap.add_argument('--script', type=Path,
                    help='a scripted session after the first map (cmd/key/xdo/wait/shot/state lines) instead of the music '
                         'and second-load steps: evidence shots and replays')
    ap.add_argument('--sweep', choices=('report', 'fail', 'off'), default='report',
                    help='dbg sweep on the first map (ENTITY-SWEEP-AB): report (default) logs its SWEEP RESULT line, fail '
                         'fails the smoke on a FAIL result, off skips it')
    # CHIM-SEYDA-BALMORA-LOAD-HANG-43, experiments E2 and E3 (remote console off; extra emulator lines)
    ap.add_argument('--remote', default=os.environ.get('AW_SMOKE_REMOTE', 'on'),
                    help='on (default): the remote-console folder drives and reads the game; off (also AW_SMOKE_REMOTE=off): '
                         'no such folder, as in a player\'s game; the route (--map, then --tp and --map in turn) runs from the '
                         'play copy\'s autoexec and is judged by screenshots of the debug HUD clock (experiment E2)')
    ap.add_argument('--route-seconds', type=int, default=600, help='--remote off: how long the route runs (600 s)')
    ap.add_argument('--route-frames', type=int, default=400, help='--remote off: frames between two moves of the route (400)')
    ap.add_argument('--shot-every', type=int, default=10, help='--remote off: seconds between screenshots (10)')
    ap.add_argument('--frozen', type=int, default=150,
                    help='--remote off: the same picture this many seconds = a stop (150, the smoke\'s load limit)')
    ap.add_argument('--emu-option', action='append', default=None, metavar='KEY=VALUE',
                    help='an extra emulator config line, e.g. deterministic=1 (experiment E3); repeatable; also '
                         'AW_SMOKE_EMU_OPTION="k=v;k2=v2"; "none" = no extra lines; checked in the emulator\'s start-up '
                         'log (a run whose option the emulator did not take fails)')
    ap.add_argument('--alternate', choices=('remote', 'emu'),
                    help='run --runs rounds of two variants in turn and count stops: remote = remote console on, then '
                         'off; emu = without, then with the --emu-option lines (remote on); OUT/counts.tsv')
    ap.add_argument('--runs', type=int, default=20, help='--alternate: rounds (20)')
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
    try:
        if args.remote not in ('on', 'off'):
            raise ValueError('--remote (or AW_SMOKE_REMOTE) must be on or off, not %r' % args.remote)
        raw = args.emu_option if args.emu_option is not None else \
            [x for x in os.environ.get('AW_SMOKE_EMU_OPTION', '').split(';') if x.strip()]
        emu_options = parse_emu_options(raw)
        autoexec = None
        if args.remote == 'off':
            if args.script or args.start != 'map':
                raise ValueError('--remote off runs the plain route only (no --script, --start map)')
            if min(args.route_seconds, args.shot_every, args.frozen) < 1:
                raise ValueError('--route-seconds, --shot-every and --frozen must be 1 or more')
            autoexec = route_autoexec(args.map, args.tp, args.route_frames, args.load_trace)
        if args.alternate == 'emu' and not emu_options:
            raise ValueError('--alternate emu needs at least one --emu-option')
        if args.alternate and args.runs < 1:
            raise ValueError('--runs must be 1 or more')
    except ValueError as e:
        print('engine smoke: %s' % e)
        print('smoke-exit=2')
        return 2
    if args.alternate:
        return alternate(args, list(sys.argv[1:] if argv is None else argv))
    want = sha256(args.engine)
    out = args.out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(args.engine, out / 'engine.AmiWind')
    (out / 'probe.sh').write_text(PROBE, encoding='utf-8', newline='\n')
    (out / 'stall.py').write_text(STALL_PY, encoding='utf-8', newline='\n')
    (out / 'judge.py').write_text(JUDGE_PY, encoding='utf-8', newline='\n')
    if emu_options:
        (out / 'emu-options.txt').write_text(emu_config_lines(emu_options), encoding='utf-8', newline='\n')
    if autoexec is not None:
        (out / 'autoexec.cfg').write_text(autoexec, encoding='utf-8', newline='\n')
    if args.script:
        shutil.copyfile(args.script, out / 'script.txt')
    (out / 'engine.txt').write_text('engine sha256 %s\nimage %s\nprofile %s\nfast ram %d MiB\nremote console %s\n'
                                    'emulator options %s\n'
                                    % (want, args.image_dir, args.prof, args.fast_mb, args.remote,
                                       ' '.join('%s=%s' % o for o in emu_options) or 'none'),
                                    encoding='utf-8', newline='\n')
    shares = ['--cpu-shares', args.cpu_shares] if args.cpu_shares else []
    base = ['run', '--pull', 'never', '--rm', '--network', 'none', *shares]
    scratch = args.scratch.strip('/')
    # LOAD-HANG-WATCHDOG-62: --load-trace turns the engine's load trace on from the play copy's autoexec (off in a
    # shipped game); a stop's examination then reads its ring (logs/loadtrace-at-stop.txt)
    trace_line = 'aw_loadtrace 1\\n' if args.load_trace else ''
    # --remote off: the route autoexec written above (OUT/autoexec.cfg), no aw_remote line
    put_autoexec = ("printf 'aw_remote 1\\n{trace_line}' > /tmp/autoexec.cfg".format(trace_line=trace_line)
                    if autoexec is None else 'cp /t/autoexec.cfg /tmp/autoexec.cfg')
    # The 4 GiB play copy past the page cache (direct I/O, holes kept): a cached copy filled the 2 GiB prep container
    # and the kernel killed it, on and off (ENGINE-SMOKE-PREP-KILLED-52)
    prep = f'''set -e
rm -rf /vol/{scratch}; mkdir -p /vol/{scratch}
B=$(ls /vol/{args.image_dir}/*.hdf | grep -v world | head -1); [ -n "$B" ]
for F in /vol/{args.image_dir}/*.hdf; do s=$(stat -c %s "$F"); if [ $((s % {IDE_CYLINDER_BYTES})) -ne 0 ]; then echo "ide-cylinders=FAILED $(basename "$F") $s"; exit 3; fi; done
echo "ide-cylinders=ok"
dd if="$B" of=/vol/{scratch}/play-boot.hdf bs=4M iflag=direct oflag=direct conv=sparse status=none; chmod u+w /vol/{scratch}/play-boot.hdf
W=$(ls /vol/{args.image_dir}/*world-01.hdf 2>/dev/null | head -1 || true); echo "world=$(basename "$W" 2>/dev/null)"
X={XDF}; D=/vol/{scratch}/play-boot.hdf
$X $D open part=DH0 + delete AmiWind + write /t/engine.AmiWind AmiWind
{put_autoexec}
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
        bad = re.search(r'^ide-cylinders=FAILED (\S+) (\d+)', r.stdout, re.M)
        if bad:
            # IMAGE-IDE-CYLINDER-TAIL-59: the emulated IDE port hides the last blocks of such a drive; the load
            # then waits for ever on Kickstart's read-error requester. Refuse before booting.
            print('engine smoke: the smoke image drive %s is %s bytes, not whole IDE cylinders (a multiple of %d): '
                  'refused before boot (IMAGE-IDE-CYLINDER-TAIL-59); pad the fixture with zeros'
                  % (bad.group(1), bad.group(2), IDE_CYLINDER_BYTES))
            print('smoke-exit=2')
            return 2
        world = re.search(r'^world=(\S*)', r.stdout, re.M)
        back = re.search(r'^readback=([0-9a-f]{64})', r.stdout, re.M)
        if r.returncode or not back or back.group(1) != want:
            print('engine smoke: preparing the play copy failed (see prep.log)')
            print('smoke-exit=2')
            return 2
        docker(*base, '--cpus', args.cpus, '--memory', '3g', '--name', args.name + '-run', '--entrypoint', 'sh',
               '-e', f'PROF={args.prof}', '-e', f'WORLD={world.group(1) if world else ""}', '-e', f'MAP1={args.map}',
               '-e', f'TP={args.tp}', '-e', f'PLAY={args.play}', '-e', f'REPEAT={max(1, args.repeat)}', '-e', f'START={args.start}', '-e', f'AFTER={args.after_load}', '-e', f'ILLEGAL={int(args.log_illegal)}', '-e', f'IDETRACE={int(args.ide_trace)}', '-e', f'LOADTRACE={int(args.load_trace)}', '-e', 'REMOTE=%d' % (args.remote == 'on'), '-e', f'ROUTESECS={args.route_seconds}', '-e', f'SHOTEVERY={args.shot_every}', '-e', f'FROZEN={args.frozen}','-e', f'KICK={args.kickstart}', '-e', f'FASTMB={args.fast_mb}', '-e', f'SWEEP={args.sweep}', '-e', 'ZONEFULL=%s' % ('allow' if args.allow_zone_full else 'fail'),
               '--mount', f'type=volume,src={args.volume},dst=/w,volume-subpath={scratch}',
               '--mount', f'type=volume,src={args.volume},dst=/img,volume-subpath={args.image_dir},readonly',
               '-v', f'{args.roms.resolve()}:/roms:ro', '-v', f'{out}:/out', args.fsuae_image, '/out/probe.sh',
               check=False, capture=False)
    finally:
        cleanup()
    steps = (out / 'logs' / 'steps.log')
    lines = steps.read_text(encoding='utf-8', errors='replace').splitlines() if steps.is_file() else []
    result = next((l for l in reversed(lines) if 'smoke RESULT' in l), 'smoke RESULT FAIL no result line')
    if 'FAIL emulator disk stall' in result and not args.no_stall_retry:
        # CHIM-SEYDA-BALMORA-LOAD-HANG-43: a file request the emulator never answered (seen only under heavy host
        # disk writes). Said as such and retried once on a fresh play copy (OUT/retry); a second stall fails.
        print('engine smoke: %s; retrying once on a fresh play copy' % result.split('smoke RESULT ', 1)[-1])
        again = list(sys.argv[1:] if argv is None else argv) + ['--out', str(out / 'retry'), '--no-stall-retry']
        return main(again)
    print(result.split('smoke RESULT ', 1)[1] if 'smoke RESULT ' in result else result)
    code = 0 if 'smoke RESULT PASS' in result else 1
    print('smoke-exit=%d' % code)
    return code


if __name__ == '__main__':
    sys.exit(main())
