# CHIM-SEYDA-BALMORA-LOAD-HANG-43: Travelling from Seyda Neen to Balmora sometimes hangs on the Loading screen (boot smoke, 2 of about 5 runs)

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 34 times; something has to be done

- Reported with v0.0.46 at 2026-10-20 20:09 +0300: Listed under Known in this build in the v0.0.46 release notes (still open at the release).
- Reported with v0.0.53-dev2 at 2026-10-26 (time not recorded): 19:14 UTC door sample: the Yassu Mine room load (ri9f4c8ccd45) stopped after its BSP while a gate ran its emulator; the next try loaded in 7.6 s
- Reported with v0.0.52 at 2026-10-26 15:58 +0200: PERSISTING: v0.0.52 final delivery, 16 MB smoke: dbg tp to Balmora did not load; game waits on SIGF_DOS, the request held by DH0 (emulator disk stall); passed in the run before
- Reported with v0.0.57-dev1 at 2026-10-30 12:19 +0200: Gate 4784 boot smoke (commit a1c00e4a, the shared gate-smoke v0.0.54 image, 32 MB Fast): the second load (balmora, load 1 of 3) was not in play, signon 1; the same image and a one-line later commit passed gate 4785.
- Reported with v0.0.58-dev3 at 2026-10-31 23:42 +0000: Also seen in play, not only on a load: in gates 4698, 4845, 4897 and 4954 the game stopped a few seconds after arriving in Seyda Neen (game clock still, the same frame on screen, no command taken), and gate 4932 examined such a stop: processor idle, the file request held by DH0. SMOKE-TALK-BOX-BLOCKS-REMOTE-57 and SMOKE-SEYDA-AGAIN-NOT-IN-PLAY-58 are closed as duplicates of this entry.
- Reported with v0.0.58 at 2026-11-01 (time not recorded): Seen again twice on v0.0.58 images: the boot smoke of the release build stopped with Seyda Neen not loaded, the game waiting on the emulator's disk request (held by DH0, the CPU idle); an in-game check session on the dev6 image stopped the same way before Seyda Neen. The rerun of the smoke is the next step.
- Reported with v0.0.58 at 2026-11-01 (time not recorded): And again on the release smoke's rerun: Seyda Neen loaded twice and Balmora twice, then the third Seyda Neen load from Balmora did not finish within the limit; the game kept running server frames on the Loading screen (no disk wait this time).
- Reported with v0.0.59-dev1 at 2026-11-01 (time not recorded): Seen again on the v0.0.59-dev1 delivery: the release hops session froze on its first map (Balmora) about 17 s in, before the first hop, after waiting for a gate's emulator run; the 32 MB boot smoke of the same image had passed. The hops step was rerun.
- Reported with v0.0.58 at 2026-11-01 03:04 +0200: Seen again in gate 5233 (source b1d45efd, a character menu change): the boot smoke got no answer to aw_music_status after the second load; all five samples showed the game waiting on a DH0 file request in exec idle. The same commit passed gate 5234 right after.
- Reported with v0.0.58-dev4 at 2026-11-01 07:49 +0000: Seen again in a gate boot smoke on the model-table branch (2bf629a1): after the Seyda Neen load the game stopped taking console commands for 60 seconds (the emulator disk stall pattern); the suite and the engine build passed. The gate was run again.
- Reported with v0.0.59-dev4 at 2026-11-02 (time not recorded): MiniWind proof session proof2 of CELL-CHANGES-59 at 2026-11-02 13:28 +0200 / 2026-11-02 11:28 UTC (FS-UAE, 32 MB Fast, the host busy with a gate suite and a reuse audit): after a quickload in Arrille's Tradehouse, dbg tp seydaneen loaded Seyda Neen and the game then stopped taking commands for 60 s; five PC samples in exec idle, waiting on SIGF_DOS with the request held by DH0.
- Reported with v0.0.59-dev5 at 2026-11-02 (time not recorded)
- Reported with v0.0.59-dev4 at 2026-11-02 12:44 +0200: FS-UAE sessions at 32 MB Fast on the seyda MiniWind (slice 1 image cc5b049 and the first-person arms image f983e6b alike) stopped on the emulator disk stall (game waits on SIGF_DOS, request held by DH0) in 6 of 9 runs between 11:57 and 12:44 +0200, with and without builds sharing the volume; the frame rate fell from about 6 to about 1 fps over the minute before each stall. Same scripts passed this morning.
- Reported with v0.0.59-dev4 at 2026-11-02 14:06 +0000: Seen twice on the Seyda Neen MiniWind at 32 MB Fast (da6c335, CELL-CHANGES-59 slice 4 checks): the game stopped taking commands about a minute after a save in Seyda Neen (the request held by DH0); a shorter session got through.
- Reported with v0.0.59-dev4 at 2026-11-02 14:49 +0200: Emulator disk stall during a first-person cost session in the Seyda Neen MiniWind (FS-UAE, 32 MB Fast, JIT); the same script ran through on the next try.
- Reported with v0.0.59-dev5 at 2026-11-02 22:46 +0200: Seen in 5 of 9 short Seyda Neen MiniWind sessions in one evening on a loaded machine (4 with JIT, 1 before the map loaded with JIT off); the same scripts passed on a retry.
- Reported with v0.0.59-dev5 at 2026-11-02 23:25 +0200: Seyda Neen MiniWind sessions, FS-UAE JIT 32 MB: disk stall on load (2 of 4 tries), host 32-56 % CPU.
- Reported with v0.0.59-dev5 at 2026-11-03 (time not recorded): JIT A/B for CELL-CHANGES-59 slice 6 (2abc9fc0 vs 0128e0c0, 4 runs each, alternating): 3 of 4 passed on each side; one disk stall (with slice 6) and one start failure (without); heap readings identical. Not caused by slice 6.
- Reported with v0.0.59-dev5 at 2026-11-03 (time not recorded): four strip sessions froze at the first take after a console-opened strip; IDE had completed its last command; one of four waited on DH0, three were in no file call; an aimed-open session on the same image did not freeze: follows the script path, not host load
- Reported with v0.0.59-dev5 at 2026-11-03 00:19 +0200: Seen again on the v0.0.59-dev5 full image (FS-UAE, JIT, 32 MB Fast, 2026-11-02): five short verification sessions in a row stalled with the game waiting on DH0 (pc 00F81478), during a teleport to the Census Office, Seyda Neen or at the start in Balmora, while gate runs used the other cores. One more session did not reach play at all. No in-game check of that batch could complete.
- Reported with v0.0.59-dev5 at 2026-11-03 01:50 +0200: A/B under the normal host load, same script: hard-file device 3 disk stalls in 12 sessions, emulated IDE port 0 in 16 (slower loads). The boot smoke now uses the IDE port; shipped presets unchanged.
- Reported with v0.0.59-dev5 at 2026-11-03 02:18 +0200: One of three short Seyda Neen MiniWind sessions stalled on an idle machine (disk request held by DH0); a retry passed.
- Reported with v0.0.59-dev5 at 2026-11-03 04:09 +0200: Gate boot smoke on a branch with the IDE disk controller (6c750516) and no engine change: the client stayed at signon 3 for the 30 s in-play wait before load 3 of 3; the unchanged rerun passed. The host was running several gates and emulator sessions. The gate log does not record the stall examination; the first sign that IDE alone may not end the stall under heavy host load.
- Reported with v0.0.59-dev5 at 2026-11-03 04:39 +0200: Still seen with the IDE disks under host load: four container-strip sessions (strip11-14, Seyda Neen MiniWind 420cb1a and 3e51c30) froze 171-183 s into play, one sample showing the game waiting on SIGF_DOS with the request held by DH0, while three other workers ran gates and emulator sessions.
- Reported with v0.0.59-dev5 at 2026-11-03 04:59 +0200: Correction to the earlier report of 2026-11-03: the container-strip sessions strip13 and strip14 stopped right after a take in the container strip (CONTAINER-STRIP-TAKE-STALL-59), and strip11 stopped with a conversation window open after E reached a person; none of them was this disk stall.
- Reported with v0.0.59-dev5 at 2026-11-03 05:07 +0200: Seen again with the disks on IDE: the v0.0.59-dev5 full image run with the integration engine 5a41c209 (FS-UAE, JIT, 32 MB Fast) stalled while loading Seyda Neen, before play; pc 00F811BC/00F828A2, no file call pending. Three Seyda MiniWind sessions of the same engine ran.
- Reported with v0.0.59-dev6 at 2026-11-03 11:28 +0200: Not this stall: the v0.0.59-dev6 smoke stop follows the dev6 engine. Idle machine, 32 MB, IDE, Seyda Neen: dev5 image+engine passed 4/4; dev6 image+engine stopped 4/4 within 12 s of arrival; dev6 image with long-frame engine 9a782c55 stopped 4/4; dev6 image with dev5 engine passed 2/2; dev5 image with dev6 engine stopped 2/2. Examined as a DH0 wait, yet the game resumed when given 240 s: long file reads in one frame. Cause in engine changes f08583e..79735378.
- Reported with v0.0.59-dev6 at 2026-11-03 12:50 +0200: The v0.0.59-dev6 test session stops in Seyda Neen were not this disk stall: the processor was busy in one 13 to 15 s frame (the player's assembled body loaded at arrival), ARRIVAL-LONG-FRAME-DEV6-59. The smoke now names such a frame a long frame (busy) and keeps this name for an idle processor with a file request held.
- Reported with v0.0.59-dev6 at 2026-11-03 15:44 +0000: v0.0.59-dev6 image 95a5bdb (FS-UAE, JIT, 32 MB Fast): the delivery hops stop on the hop from Ald'ruhn to Khuul 3 times of 3, twice on a quiet machine; the load stops right after vf0271's bsp, the game waits on SIGF_DOS with the request held by DW0, still so after 90 s. The same hop passed in the v0.0.57-dev5, v0.0.58-dev5 and v0.0.59-dev5 deliveries.
- Reported with v0.0.59-dev6 at 2026-11-03 18:36 +0200: Not this stall: the dev6 Khuul hop stop (3 of 3 on IDE) was Kickstart's read error requester on AW_WORLD0 block 2480045. On the IDE port the drive is read as whole 16x63 cylinders and the drive ended 144 sectors short; the dev5 image fails the same on IDE, both pass on the hard-file device. Fixed in the image step (drives padded to whole IDE cylinders, ad3c345e, gate 6660); hops and Khuul repro pass on a padded dev6 copy.
- Reported with v0.0.60 at 2026-11-05 05:49 +0200: Candidate cause under investigation, not confirmed: FS-UAE 3.1.66 updates a shared interrupt-request word without atomic operations, so a finished hard-file request can lose its signal under host load. Checks next: source, a capture at a stall, an atomic emulator build A/B, the Pi 4B. See SMOKE-STALL-LABEL-INFERRED-60.
- Reported with v0.0.61-dev1 at 2026-11-05 23:16 +0200: Delivered image (run 2026_11_05_v0.0.61-dev1_full-v0.0.61-dev1_374d59b), FS-UAE 3.1.66 at 32 MB Fast, JIT, disks on IDE, a busy host: dbg scene seyda after a quickload in Arrilles Tradehouse stopped with the game clock frozen; the stall check found 5 of 5 program counter samples in exec idle, the game waiting on SIGF_DOS, no request holder found. 5 earlier sessions of the same image the same evening passed their Seyda Neen loads.
- Reported with v0.0.61 at 2026-11-07 03:39 +0200: Release image: a coordinate teleport from Seyda Neen to Ebonheart about 60 s after arrival stopped the game: the clock stood still, the processor idle and the game waiting on a file request no handler held. The emulator was not under load at the time. The same teleport worked in the session before and in the rerun.
- Reported with v0.0.61 at 2026-11-07 05:21 +0200: The v0.0.61 release image on the emulator (32 MB Fast, JIT, busy host): the second load of Seyda Neen at the start of a scripted session stopped at the second sign-on step and stayed on the Loading screen; the same script prefix loaded normally in the session before.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 18 October 2026, in v0.0.43-dev1 |
| Where | file request to the boot partition (DH0) never answered, under host load; seen on map changes |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.43-dev1 (last seen) |
| Severity | high: the game can stop on a Loading screen; seen on the v0.0.41-dev5 image (gate 2928) and on v0.0.43-dev1 (first smoke), each passing on a rerun |
| Family | CHIM world streamer (`chim-streamer`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_17_v0.0.43-dev1_full-batch2_7ac15b1 |
| From commit | source 7ac15b1, engine 7ac15b1, CHIM world 7ac15b1 |
| CHIM engine version | CHIM 0.2.1, engine 7ac15b1, world format unknown |
| Unknown because | the smoke run does not record the world format |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev1 (5 November 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 34 times; something has to be done](#persisting-reported-34-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Hypotheses and the test plan](#hypotheses-and-the-test-plan)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The FS-UAE boot smoke boots the game, loads Seyda Neen, then travels to Balmora (`dbg tp -21800 -12300`). In two of
about five runs on 17-18 October 2026 the Balmora load printed its first steps (after the map, after the actors,
"Balmora") and then stayed on the Loading screen; the smoke reported "did not load a map (server seyda)". The same
image passed on a rerun each time.

Reproduced on 18 October 2026 with a repeat loop (below): five more hangs, four on the way to Balmora and one on the
way back to Seyda Neen. A hung load never finished: one hang was still there after 10 minutes.

## Where

Not in the map change itself. In all five hangs caught with the emulator's debugger, the game was waiting inside an
ordinary file call (an `open()` or a read during a model, sprite, inventory or combat-data load) for a request it had
handed to the file system of the game disk's boot partition (DH0, the Kickstart Fast File System on the emulator's
hard-file device), and the answer never came. Seen on two images: the v0.0.41-dev5 regional image (gate 2928,
17 October 2026) and the v0.0.43-dev1 build 2026_10_17_v0.0.43-dev1_full-batch2_7ac15b1.

## How it happened

What the debugger showed in each of the five hangs (12 of 12 program-counter samples, one per second, plus a walk of
every task's state and message port):

- The processor sat in Kickstart's idle loop (`$00F81476`, STOP): no task was running. This is a deadlock, not
  a slow load and not a loop in the engine: nothing was computing.
- The game process waited for the file-system reply signal (SIGF_DOS). Its own reply port was empty: no reply had
  arrived.
- The request packet on the game's stack was linked into the message list of DH0's port. The DH0 handler had
  taken it (its port was empty) and was asleep in its main wait, without answering. The world disk's handlers
  (DW0, DW1) and the remote-console folder (AWCTL) were idle and not involved.
- The engine call sites differed every time (a model load in the server's precache, a sprite, the inventory data,
  the combat data). The only thing in common was the file system of DH0.

So a file request to DH0 was taken and never completed below the engine: in the emulator's hard-file path (most
likely an I/O completion lost under host load) or inside the file system handler. This is the same class as the two
older freezes SEYDA-LOAD-HANG-30 (a read that never returns during a Seyda Neen load) and HANG-IDLE-DUSK-35 (the
music read that never returns). The engine stops reading music synchronously since v0.0.36, but every other file
call is still a normal blocking call.

Seyda Neen's full CHIM zone ("zone full ... retrying") and the low hunk gap when it is left are not the cause: the
hangs come with and without them (see Reproduction, 128 MiB).

## Why it was not caught

The boot smoke made one map change per run and passes most of the time, so single green runs hid it; the earlier
failure on the old image was taken for a flaky smoke and rerun. The hang needs a loaded machine: on a quiet machine it did
not happen in 100 loads.

## Reproduction

Sometimes, and only with the host busy. Repeat loop (private hunt tool): fresh play copy, boot to the console, load
Seyda Neen, music off as in the smoke, then `dbg tp` Balmora / Seyda Neen back and forth, a load counted as hung
after 90 to 600 s, the debugger attached. All runs: the v0.0.43-dev1 image and engine (sha256 d9a21a39...), FS-UAE
3.1.66, JIT preset, 68040, 2 cores per session, 18 October 2026.

| Runs | Fast RAM | Host | Loads | Hangs |
| --- | --- | --- | --- | --- |
| 3 sessions, 6 s per map | 16 MiB | quiet | 48 | 0 |
| 3 sessions, 6 s per map | 128 MiB (95 MiB CHIM cache, no "zone full") | quiet | 48 | 0 |
| 3 sessions, 20 s per map | 16 MiB | CPU + disk load beside it | 22 | 1 |
| 5 sessions, 15 s per map | 16 MiB | CPU + disk load | 100 | 0 |
| 6 sessions, 3 s per map | 16 MiB | CPU + disk load, play copies prepared and removed beside it | 239 | 4 |
| 9 sessions, 3 s per map (hard-file device, A/B) | 16 MiB | CPU load, then disk load | 720 | 0 |
| 9 sessions, 3 s per map (boot disk on the emulated IDE port, A/B) | 16 MiB | the same | 550 | 0 |

Six unmodified boot smokes beside the loaded loop all passed. All five hangs came in two windows in which several
play copies (2.2 GB each) were being copied into or removed from the Docker volume beside the running sessions, as
in the two original failures (a test-suite container, a source package build). A steady synthetic load (busy
processors, repeated 1.6 GB writes) did not bring them back, so the hard-file versus IDE comparison could not
decide at this rate.

## Repair

Open: an emulator disk stall during heavy host write bursts, under observation. Real hardware is not believed to be
affected (it has no host-side hard-file path), but this is not proven. Next:
1. On the next capture, read the DH0 handler's pending device request and the emulator's hard-file queue to name
   the layer that loses it (emulator hard-file device or the file system).
2. Find a trigger that brings it back on demand (several 2 GB play copies written and deleted on the Docker disk
   while sessions run), then repeat the hard-file versus IDE A/B with it.
3. Then decide: the emulated IDE port for the boot disk in the shipped FS-UAE and WinUAE presets, a newer emulator,
   or a bounded wait in the engine's own file reads (the music reader's pattern, aw_aread.c) for map loads.

3 November 2026, under the normal working load (other gates and sessions, host 4-88 % CPU), v0.0.59-dev5 full
image, FS-UAE 3.1.66, JIT, 32 MB Fast, the same script (boot, Seyda Neen, Balmora, Seyda Neen), alternating:

| Disk device | Sessions | Disk stalls |
| --- | --- | --- |
| hard-file device (uaehf.device, as shipped) | 12 | 3 |
| emulated A1200 IDE port (Kickstart scsi.device) | 16 | 0 |

On IDE the loads are slower: the same script took about 127 s against about 98 s, and a teleport load took over 20 s
where the hard-file device took under 20 s. Every IDE session that a 20 s wait reported as not in play had loaded the
map 60 s later (4 of 4 checked). The boot smoke (`tools/engine_smoke.py`) and the session tool now put the disks
on the IDE port. The shipped presets still use the hard-file device: moving them costs players load time and is a
separate decision.

Later the same night (3 November 2026), with four to six test jobs running emulator sessions and gates beside each
other:

- Four container-strip sessions that froze 171-183 s into play were first reported here as this stall. They were
  not: the emulated IDE drive had finished every command, the processor samples were in the game's own code, and the
  game went on after about 10 s. That is a separate long frame in Arrille's Tradehouse (TRADEHOUSE-LONG-FRAME-59).
- One gate boot smoke on IDE stopped with the client at signon 3 for the whole 30 s wait before its third load; the
  unchanged rerun passed. No stall sample was taken, so whether it was this stall is not known. It is the only
  possible sign of a stall on IDE so far.
- Gate smokes failing on "CHIM zone full" were not this bug either: the boot loop typed a command while the
  start-up logo was up and turned the CHIM cache off for that start (SMOKE-M-KEY-SKIPS-CHIM-CACHE-57, fixed).
- To keep the host load down, at most two emulator sessions now run at once on the build machine (the session tool
  and the gate smoke wait for a free slot).

Decision (the maintainer, 3 November 2026): the shipped FS-UAE and WinUAE presets and the Raspberry Pi 4 image keep
the hard-file device for now. The Pi 4 image (Amiberry), the project's measuring machine, is the next test: the
presets move to the IDE port only if a stall shows up there or in play, since IDE makes every load about 30 %
slower.

## Hypotheses and the test plan

5 November 2026. The cause is not found. What is known, what is suspected, and how each suspicion will be tested.

**Known**
- The stall is strongly associated with host load, but it is not shown to require it: one apparent stall on an idle
  host (3 November, 1 of 3 sessions) may need reclassifying.
- In the stalls that were examined, the game waits idle on a reply from DH0 (the processor in exec's idle loop, the game
  waiting on SIGF_DOS).
- It was seen once with the JIT off, so it is not tied to the JIT.
- Hard-file device 3 stalls in 12 sessions against emulated IDE 0 in 16 (the table above); the IDE runs were also
  about 30 % slower, so that comparison changed both the completion path and the timing.
- The test sessions have used IDE since 3 November, and no stall has been seen in the deliveries since.

**A lost disk-done signal in the emulator (candidate, unconfirmed).** FS-UAE 3.1.66 appears to update one shared
interrupt-request word with plain read-modify-write operations, from the hard-file worker thread (which sets the bit
that announces a finished request) and from the emulation thread (which clears the bits of other devices). If the two
interleave, the announcement can be overwritten and the reply stays queued with nobody told. Upstream changes make
these updates atomic: FS-UAE 4eefeebd0947bb7b08fae3b9b4f1735376897aaf with the helpers in
11eca645d849bb558bfdea25bedd0fabde56196a, and WinUAE 0cc79925fa5f3092f4a103066e140cbf9980b9f2 and
7da6a52378d074a4b030aca951172cf183286045. The files concerned appear identical in FS-UAE 3.1.66 and 3.2.35. Whether
the absence of these changes causes our stalls is not established. The point is to be checked against the source of
the package the test containers use.

**The remote-console folder may take part.** The older freeze HANG-IDLE-DUSK-35 needed heavy traffic on the
remote-console folder (AWCTL, a directory drive). An upstream report describes repeated file operations on directory
drives leaving a guest task stuck, prevented by `deterministic = 1`. That setting serialises directory drives only; the
hard-file worker is not affected. A result with it therefore tests AWCTL's part, not the lost disk-done signal, and its
slowdown could also hide a race. Both can be true.

**The smoke's stall label is inferred (verified).** The smoke labels a stall "emulator disk stall" from a scan of
the game's stack, without checking the pending device request. The label means the guest waits on DOS and the cause
below the engine is unresolved; it does not show a lost device completion. Some of the sightings counted here were
later reclassified (long frames, a read error on IDE), so only the confirmed captures count towards this mechanism.
Tracked as SMOKE-STALL-LABEL-INFERRED-60.

**The test plan** (cheap first, all in the test containers)
1. Read the FS-UAE 3.1.66 source: the interrupt-request word, every writer, and the four upstream changes. Confirm or
   reject the mechanism of the lost disk-done signal in the source.
2. Capture a sustained stall with all emulator threads stopped: the request the guest waits for, the queue of
   replies to deliver, the interrupt-request word, and the state of each host thread. Setting the missing bit again and
   seeing the load continue at once shows that the signal was stranded.
3. A/B with a build in which every access to that word is atomic, against the original, in alternating runs with the
   same image, script and background load (running both together disturbs both). It counts only if the original
   reproduces the captured failure repeatedly and the patched build survives the same exposure.
4. `deterministic = 1` in a copy of the session preset, checked in the start-up log: this tests the remote-console folder's part.
5. The same route on the Raspberry Pi 4B (Amiberry, a quiet machine). A stall only on the busy build machine is host
   load; a stall on the Pi as well is a bug in the game or the disk image.

**For players.** The shipped presets are unchanged and keep the hard-file device until this is verified. If the lost disk-done signal is confirmed,
the decision is to provide or name a corrected emulator build, document the affected emulator versions, and decide
whether an IDE profile stays useful for those who run unpatched builds. Results on the Pi (Amiberry) are kept apart,
since it is a different emulator.

## Verification

Pending: needs the repair. A repair is verified by the repeat loop with the same I/O bursts: many loads with no
hang, where the unrepaired setup hangs.

## Prevention

The boot smoke (`tools/engine_smoke.py`) now:
- runs its map change three times (`--repeat`, default 3, back to the first map in between), so an intermittent
  load hang has three chances to show up in every smoke instead of one;
- runs FS-UAE with its monitor on a pseudo-terminal and, when a load does not finish, examines it in place
  (`stall.py`: five program-counter samples one second apart, exec's task lists, the game's waiting request). The
  stall described above is reported as "emulator disk stall (CHIM-SEYDA-BALMORA-LOAD-HANG-43)" and the run is
  retried once on a fresh play copy; a second stall fails the smoke. Any other stall fails at once with what the
  monitor saw.

Checked in the emulator, 18 October 2026, on the v0.0.43-dev1 image: the smoke passed with its map change run three
times (105 s); a smoke asked to load a map that does not exist stopped with "STALL unknown: pc 0 of 5 samples in exec
idle; game not in a file call" (the monitor check ran live and did not mistake a missing map for a disk stall).

Fly-cam check, 18 October 2026: noclip flight Seyda Neen -> Vivec -> Balmora -> Khuul with the music on
(about 300,000 units, 38 to 40 map and frame changes, about 290 s, under 3 times walking speed), at 16 MiB and at
128 MiB Fast RAM on a quiet machine: both completed, no stall. At 16 MiB, 267 "zone full" lines and 12 hunk-gap
warnings; at 128 MiB, no "zone full" and the same 12 warnings.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: CHIM world streamer (`chim-streamer`). The CHIM streamer keeps Quake's visibility effective and its renderer counters must not get worse. See [families](README.md#families).

- [BUILD-CHIM-HEAP-GATE-LATE-36](BUILD-CHIM-HEAP-GATE-LATE-36.md): The CHIM heap gate runs after the stair walk: a ring over the zone is found 69 minutes late
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36](BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): CHIM frames are stair-walked again on every build: about 69 minutes for 270 frames
- [BUILD-CHIM-VALIDATE-LATE-36](BUILD-CHIM-VALIDATE-LATE-36.md): The CHIM world is validated only after the whole chim stage: a bad chunk is found 45 minutes in
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36](BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): The image step of a CHIM-native town read legacy region maps that are never built: the Bitter Coast test build failed at the end of its image step on maps/bc000.bsp
- [BUILD-LEGACY-CHAIN-DEFAULT-36](BUILD-LEGACY-CHAIN-DEFAULT-36.md): Builds still prepared CHIM towns through the legacy region-map chain by default, and a retired flag (--legacy-area) was accepted with only a warning
- [CHIM-ACTOR-RING-33](CHIM-ACTOR-RING-33.md): A scripted actor step could move the CHIM chunk ring to the actor
- CHIM-ACTOR-SPAWN-HITCH-54 (no report page): A joining cell's actor spawns cost 5 to 135 ms a tick: the first model load of one mudcrab took 135 ms, ten spawns took 502 ms
- [CHIM-ACTOR-TABLE-OFF-IN-GAME-47](CHIM-ACTOR-TABLE-OFF-IN-GAME-47.md): The actor table ships in v0.0.47-dev2, but the engine does not read it by default
- [CHIM-ACTORS-OUTSIDE-RING-33](CHIM-ACTORS-OUTSIDE-RING-33.md): Actors outside the CHIM ring have no terrain collision
- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47](CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): With the type 1 window and the actor table, a town is empty after the player comes back into it from the region frames
- [CHIM-ALIAS-STATIC-HUNK-35](CHIM-ALIAS-STATIC-HUNK-35.md): Streamed alias statics load into the cache mid-map without being counted in the map's Hunk rest
- [CHIM-ANIM-TEXTURES-33](CHIM-ANIM-TEXTURES-33.md): Animated shared textures in CHIM show only their first frame
- [CHIM-ARENA-MEMORY-33](CHIM-ARENA-MEMORY-33.md): The Vivec Arena does not fit the CHIM zone: canton bodies are single models of 1.4-2.5 MB
- [CHIM-BALMORA-INSET-SLIVERS-43](CHIM-BALMORA-INSET-SLIVERS-43.md): Balmora's town frame hands over 96 units inside its cells: the 8 cells around the town keep classic strips, built as 15 legacy maps (11.5 MB) with every object of those cells
- [CHIM-BALMORA-LIGHT-ROOM-33](CHIM-BALMORA-LIGHT-ROOM-33.md): Balmora's CHIM active ring has 2,528 bytes of headroom: no stored lighting fits
- [CHIM-BORDER-COLLISION-33](CHIM-BORDER-COLLISION-33.md): Collision near CHIM chunk borders ignores the neighbour chunk's ground
- [CHIM-BRUSH-BAD-DATA-35](CHIM-BRUSH-BAD-DATA-35.md): A damaged or truncated CHIM model or terrain image ends the game (Sys_Error) instead of failing that load
- [CHIM-CHUNK-LOAD-FAIL-33](CHIM-CHUNK-LOAD-FAIL-33.md): Balmora chunks fail to load on CHIM, never recover, and leave holes without ground
- [CHIM-COMPILED-HULL-OVERFILL-46](CHIM-COMPILED-HULL-OVERFILL-46.md): CHIM model standing hulls without edge bevels are solid where their own collision pieces leave room: up to 82 units, mostly in open air
- [CHIM-COMPILED-HULL-SHORT-36](CHIM-COMPILED-HULL-SHORT-36.md): Compiled standing hulls lose pieces: terrain up to 3 units below the ground, Hlaalu houses up to 139 units
- [CHIM-CROSSING-SLUGGISH-43](CHIM-CROSSING-SLUGGISH-43.md): Crossing between CHIM cells is sluggish, worst at cell corners
- [CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): The seam-tear audit does not measure the CHIM detail budgets: the Vivec statues at 900 of 5,451 triangles are not checked for opened seams
- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [CHIM-EFRAG-UNCAPPED-35](CHIM-EFRAG-UNCAPPED-35.md): CHIM placements link efrags without a cap: a large ring can reach the efrag pool limit and end the map (Host_Error)
- [CHIM-EMPTY-POINT-HULL-36](CHIM-EMPTY-POINT-HULL-36.md): A CHIM model without collision has no point-hull node: the engine reads it as solid, or refuses it on load
- [CHIM-EXTERIOR-ACTORS-MISSING-46](CHIM-EXTERIOR-ACTORS-MISSING-46.md): Most outdoor NPCs and every outdoor creature are missing: region frames place no actors (93 of 566 exterior NPC references, 0 of 5,415 creature references)
- [CHIM-FAR-BAND-GAP-36](CHIM-FAR-BAND-GAP-36.md): From a CHIM area's border the ground ends at the frame edge: up to 476 units with no land before the fog plane
- [CHIM-FAR-OBJECTS-33](CHIM-FAR-OBJECTS-33.md): Houses between the CHIM ring and the legacy overlap depth are missing from the fogged horizon
- [CHIM-FAR-TERRAIN-33](CHIM-FAR-TERRAIN-33.md): A CHIM frame has no distant ground: beyond the active ring the land is missing (empty valleys, Vivec not visible from the world)
- [CHIM-FERN-NCO-SOLID-38](CHIM-FERN-NCO-SOLID-38.md): Fire ferns marked NCO become solid in CHIM mesh conversion
- CHIM-FRAME-16MB-REFUSAL-48 (no report page): Five CHIM region frames are over or within 64 KiB of the 16 MB heap budget: on 16 MB of Fast RAM (or with Extra RAM off) their rings may not fit the zone
- [CHIM-FRAME-COORD-RANGE-33](CHIM-FRAME-COORD-RANGE-33.md): One Vivec city frame does not fit Quake's coordinate range (network coordinates are 1/8-unit shorts)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36](CHIM-FRAME-EDGE-EFRAG-CRASH-36.md): R_StoreEfrags: Bad entity type 270440 ends the game: a leaf link to an entity whose model is NULL (normal play in Seyda Neen; noclip past the Vivec frame edge)
- [CHIM-FRAME-GROUND-TRACE-38](CHIM-FRAME-GROUND-TRACE-38.md): CHIM image assembly exceeds collision traversal guard in cell 6,-5
- [CHIM-FRAME-WORLD-BOUNDS-33](CHIM-FRAME-WORLD-BOUNDS-33.md): A CHIM frame map must carry an empty world whose bounds cover the frame
- [CHIM-FROZEN-ACTORS-33](CHIM-FROZEN-ACTORS-33.md): Frozen CHIM actors: projectiles stop mid-air and timers stop
- [CHIM-GRAFT-FAIL-NO-FLOOR-35](CHIM-GRAFT-FAIL-NO-FLOOR-35.md): A CHIM map whose frame world cannot start loses its far terrain too: the player may spawn over void
- [CHIM-GRAFT-REPACK-EMPTY-33](CHIM-GRAFT-REPACK-EMPTY-33.md): A frame world repack without room for the whole ring drops every chunk: the world vanishes and the player falls under Seyda Neen
- [CHIM-HANDOFF-POPIN-36](CHIM-HANDOFF-POPIN-36.md): Most of a CHIM area's objects are not drawn from the legacy side and appear at the handover (Gnaar Mok, a Dwemer ruin)
- [CHIM-HARVEST-NAMING-33](CHIM-HARVEST-NAMING-33.md): A town-wide CHIM harvest catalogue does not fit the name and size limits
- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map
- [CHIM-HEAP-INT-MATMUL-36](CHIM-HEAP-INT-MATMUL-36.md): The CHIM heap scan multiplies 0/1 tables as int32: numpy's plain loop, 6 of 24 cores, about 60 s per check
- [CHIM-HIDDEN-FACES-33](CHIM-HIDDEN-FACES-33.md): CHIM draws placed-model faces under the terrain that the recorded Seyda Neen region maps cull
- [CHIM-HULL-CHAIN-COST-33](CHIM-HULL-CHAIN-COST-33.md): Large placed models collide through one long chain of convex pieces: a trace near the Arena canton walks about 6,600 planes
- [CHIM-HULL-ROUTE-NO-CUT-43](CHIM-HULL-ROUTE-NO-CUT-43.md): Two flora meshes keep a standing hull that is one chain over the depth limit although routed: 14 cells fail the hull audit (hull policy pending)
- [CHIM-HULL2-33](CHIM-HULL2-33.md): CHIM terrain uses the player hull for large entities
- [CHIM-LAVA-RECOVER-38](CHIM-LAVA-RECOVER-38.md): Debug recovery fails to find a clear spawn after lava contact
- [CHIM-LAVA-TERRAIN-AUDIT-37](CHIM-LAVA-TERRAIN-AUDIT-37.md): Terrain validation omits lava beds, surfaces and contents
- [CHIM-LEAF-SPAN-33](CHIM-LEAF-SPAN-33.md): 160 of 1,488 Balmora placements span more than 16 leaves
- [CHIM-LIGHT-CONTENTS-33](CHIM-LIGHT-CONTENTS-33.md): Actor lighting and water contents ignore CHIM chunks
- [CHIM-MEASURE-EMPTY-FRAME-33](CHIM-MEASURE-EMPTY-FRAME-33.md): CHIM world measurement stops on a frame without models (every empty sea cell)
- [CHIM-MESH-PROFILE-SPLIT-36](CHIM-MESH-PROFILE-SPLIT-36.md): Seyda Neen converts the same meshes with other profiles than the other CHIM areas (texture size 64 against 32, no surface collision rule), so they are stored twice
- [CHIM-MIPTEX-OFFSET-UNCHECKED-35](CHIM-MIPTEX-OFFSET-UNCHECKED-35.md): CHIM texture mip offsets are taken from disk unchecked: a wrong offset makes the rasterizer read past its block
- [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md): Placed CHIM models reserve renderer nodes that their point-hull loader never allocates
- [CHIM-MOLAG-MEMORY-38](CHIM-MOLAG-MEMORY-38.md): Tel Uvirith exterior cell (10,1) exceeds the CHIM active-ring memory budget
- [CHIM-OCEAN-CELL-RECORD-CLASSIC-43](CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md): 14 open-sea cells with a CELL record and no LAND stay classic: the build keeps a legacy map for each, the tracker counts them as open ocean and no cell list selects them
- [CHIM-OCEAN-CELL-RECORD-ROUTING-43](CHIM-OCEAN-CELL-RECORD-ROUTING-43.md): The dev3 full build stops 30 minutes in, in world terrain: the 14 open-sea cells with a CELL record are routed as map-less ocean cells although each has an open-world map
- [CHIM-PACK-DIRS-33](CHIM-PACK-DIRS-33.md): CHIM pack directories are fully resident and would grow to about 400 KB for the island
- [CHIM-PACK-LRU-STREAM-35](CHIM-PACK-LRU-STREAM-35.md): A streamed model keeps a sector file handle the four-file cache may close: the next stream step reads a closed file
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)
- [CHIM-PLACEMENT-MARGIN-COPIES-46](CHIM-PLACEMENT-MARGIN-COPIES-46.md): Every object placement is stored in about 3.5 frames (the region frame margins) plus 619,074 reach copies: 52 MB of placement records for 132,369 objects
- [CHIM-PLANE-TYPE-ALL-SLANTED-46](CHIM-PLANE-TYPE-ALL-SLANTED-46.md): Every CHIM plane is stored as slanted (type 3), so axial planes never take Quake's fast paths in collision and drawing
- [CHIM-PREDICT-VIVEC-LOW-36](CHIM-PREDICT-VIVEC-LOW-36.md): The CHIM memory predictor under-predicts every Vivec district frame by 28-54 %: Vivec architecture decodes to 1.3-2.3 times the bytes per triangle it was fitted on
- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [CHIM-READ-BUDGET-33](CHIM-READ-BUDGET-33.md): CHIM per-frame read budget can be exceeded by a whole lump
- [CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): Each CHIM crossing rebuilds the whole frame world; the cost is not measured
- [CHIM-RECEIPT-COMMIT-33](CHIM-RECEIPT-COMMIT-33.md): CHIM world receipts do not record the commit the world was built from
- [CHIM-RECIPE-APRON-SCOPE-41](CHIM-RECIPE-APRON-SCOPE-41.md): Regional aprons lose original-cell visual recipes and regress the memory gate
- [CHIM-RED-MOUNTAIN-SOLID-SKY-43](CHIM-RED-MOUNTAIN-SOLID-SKY-43.md): On the Red Mountain summit (cell 2,9) the player ends up inside solid and only the sky is drawn, no terrain
- [CHIM-REGION-DIVIDED-CELLS-36](CHIM-REGION-DIVIDED-CELLS-36.md): Most converted land cells cannot switch to CHIM inside the open world: the legacy builder split them over several maps and a region frame replaces exactly one
- [CHIM-REGION-MARGIN-STORAGE-36](CHIM-REGION-MARGIN-STORAGE-36.md): One-cell CHIM region frames store about 3.5 times their cell's terrain (the terrain-only margin)
- [CHIM-REGION-POCKET-TOWN-CELLS-42](CHIM-REGION-POCKET-TOWN-CELLS-42.md): The legacy-pocket rule counts cells wholly inside a town frame as legacy: CHIM region cells around a town are left out for nothing
- [CHIM-REGION-SEABED-NO-HEIGHTS-42](CHIM-REGION-SEABED-NO-HEIGHTS-42.md): The full build refuses the 98 heightless seabed cells as region cells (no original LAND), without naming the cell, although CHIMport converts them
- CHIM-ROOM-16MB-REFUSAL-48 (no report page): On 16 MB of Fast RAM (or with Extra RAM off) a CHIM room larger than the zone ended the game with a host error at its door
- [CHIM-ROOM-BLANK-WALLS-54](CHIM-ROOM-BLANK-WALLS-54.md): Our capture camera stood inside a booth wall in Desele's House: the room drew blank from there; not visible to a player
- [CHIM-ROOM-EFRAG-LIMIT-48](CHIM-ROOM-EFRAG-LIMIT-48.md): The efrag pool limit can leave CHIM room placements undrawn in large rooms
- [CHIM-ROOM-ESTIMATE-48](CHIM-ROOM-ESTIMATE-48.md): 27 rooms set aside as too large for a CHIM room by a wrong estimate
- [CHIM-ROOM-HARVEST-DOUBLE-48](CHIM-ROOM-HARVEST-DOUBLE-48.md): CHIM rooms kept harvestable mushrooms in their room records: the image stopped on addamasartus (8 record placements not in the room map), and batch rooms had unpickable mushrooms
- [CHIM-ROOM-POPIN-51](CHIM-ROOM-POPIN-51.md): Some large interiors, in Vivec above all, are still loading in after the player has arrived: models appear while you look
- [CHIM-ROOM-STORE-SWITCH-DROPS-MODELS-48](CHIM-ROOM-STORE-SWITCH-DROPS-MODELS-48.md): Switching CHIM room stores drops the kept models
- [CHIM-ROOM-SURFCACHE-LIGHT-48](CHIM-ROOM-SURFCACHE-LIGHT-48.md): The surface cache must rebuild when the same model is drawn at different room light levels
- [CHIM-ROOMS-WATER-LAVA-48](CHIM-ROOMS-WATER-LAVA-48.md): Rooms with water or lava are not converted to CHIM rooms yet
- [CHIM-SEYDA-ACTOR-CONTACT-33](CHIM-SEYDA-ACTOR-CONTACT-33.md): rc1 image step refuses Seyda Neen's CHIM frame map: six actors stand 0.8-3.3 units off the CHIM ground
- [CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43](CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43.md): CHIM model variants take only the mesh-wide exact-bevel flag: stair plates marked for exact standing bevels get the approximate axial hull
- [CHIM-STAIR-STEPS-SOLID-43](CHIM-STAIR-STEPS-SOLID-43.md): Three stair meshes fail the CHIM stair walk: Redoran steps start in solid (Ald-ruhn, Maar Gan), Hlaalu steps blocked (Suran), a rope bridge starts in solid (0,8)
- [CHIM-STATIC-PLACE-HOST-ERROR-35](CHIM-STATIC-PLACE-HOST-ERROR-35.md): Bad flora data at CHIM chunk activation ended the session with zone locks held; the next map then stopped the program
- [CHIM-STATICS-FALLBACK-41](CHIM-STATICS-FALLBACK-41.md): A frame map with more than 512 streamed statics crashes when its CHIM world cannot load, instead of running without its chunks
- [CHIM-STITCH-SHORELINE-36](CHIM-STITCH-SHORELINE-36.md): A CHIM area in the legacy world has no shoreline refinement: steps of up to 28 units at its border
- [CHIM-TERRAIN-GRAFT-33](CHIM-TERRAIN-GRAFT-33.md): CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude
- [CHIM-TERRAIN-HULL-BEVELS-33](CHIM-TERRAIN-HULL-BEVELS-33.md): A standing box rests above the ground at convex CHIM terrain edges
- [CHIM-TEXTURE-SPECKS-33](CHIM-TEXTURE-SPECKS-33.md): CHIM-drawn surfaces show bright single-texel specks that legacy frames do not
- [CHIM-TILT-VARIANTS-SPLIT-33](CHIM-TILT-VARIANTS-SPLIT-33.md): Tilted placements each get their own model variant: 39,103 extra model variants on the base island, breaking store-once
- [CHIM-TOWN-HEAP-ROUTED-HULL-36](CHIM-TOWN-HEAP-ROUTED-HULL-36.md): With the routed terrain hull for every chunk, Balmora and Seyda Neen rings no longer fit the CHIM zone
- [CHIM-UNIT-CACHE-RACE-33](CHIM-UNIT-CACHE-RACE-33.md): Two processes storing the same CHIM unit at once: the second rename fails
- [CHIM-UNIT-FP-SOURCE-LAYOUT-33](CHIM-UNIT-FP-SOURCE-LAYOUT-33.md): The same mesh is converted again for every source stage: CHIM mesh unit fingerprints include archive offsets and texture list positions
- [CHIM-VALIDATOR-ORDER-33](CHIM-VALIDATOR-ORDER-33.md): The CHIM validator walk depended on Python string hashing
- [CHIM-VARIANT-YAW-DUPLICATES-36](CHIM-VARIANT-YAW-DUPLICATES-36.md): One CHIM model variant is stored several times: each frame builds it at the yaw of its own first placement
- [CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md): Model faces dominate each Balmora view: the streamer alone does not fix frame rate
- [CHIM-VIEW-LEAF-NO-PVS-35](CHIM-VIEW-LEAF-NO-PVS-35.md): A view leaf without a visibility row draws everything, with no counter saying so
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33](CHIM-WINDOW-MOUNT-CROSS-CELL-33.md): A one-cell CHIM frame stops when a window placed in it mounts on a facade placed in the next cell
- [CHIM-WORLD-AUDIT-SCALING-33](CHIM-WORLD-AUDIT-SCALING-33.md): The CHIM world audits grow much faster than the world: the heap gate took 3.6 s for 171 frames, 473 s for 331, and over an hour for 844
- [CHIM-WORLD-INDEX-FILE-LIMIT-36](CHIM-WORLD-INDEX-FILE-LIMIT-36.md): The engine refuses a CHIM world index with more than 4096 file rows; the dev3 coast world has 7,236, so every CHIM frame map fails
- [CHIM-YAW-PLAYER-BOX-TURNS-46](CHIM-YAW-PLAYER-BOX-TURNS-46.md): The player collision box turns with a yawed CHIM model (OpenMW keeps it world-aligned)
- [CHIM-ZONE-RELEASE-FLICKER-42](CHIM-ZONE-RELEASE-FLICKER-42.md): Full CHIM zone: distant buildings pop in and out while standing still, and the retry costs frames
- [CHIM-ZONE-RING-THRASH-33](CHIM-ZONE-RING-THRASH-33.md): Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes
- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec
- [CHIM-ZONE-UNSATISFIABLE-EVICT-35](CHIM-ZONE-UNSATISFIABLE-EVICT-35.md): The CHIM zone evicts every unlocked block for a request no free run can hold
- [CHIMPORT-OCEAN-LAND-41](CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells (land records entirely under water) are marked open ocean: CHIMport never plans them and the ocean admission refuses them
- [CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): CHIMport --retry-failed cannot rerun a lava cell of the island run: its stored source stage predates the lava conversion
- [CHIMPORT-SEABED-NO-ISLAND-42](CHIMPORT-SEABED-NO-ISLAND-42.md): Seabed cells measured as empty sea lose their island in the tracker: they drop out of the published reference and the build calls them unknown
- [COMBAT-PURSUIT-SLOPE-STALL-46](COMBAT-PURSUIT-SLOPE-STALL-46.md): A pursuer stops on a walkable slope: an actor step was refused when it moved more than a stair height along the slope
- IMAGE-FORMATS-CHIM-ROOMS-48 (no report page): The payload preflight stops a CHIM rooms build: the image step does not know the room store and room record formats
- IMAGE-ROOM-MAPS-ENGINE-REFUSED-48 (no report page): Every CHIM room is refused at its door and the game hangs on Loading: the engine accepts a .chim map only with a CHIM frame key
- IMAGE-ROOM-MAPS-FINGERPRINT-48 (no report page): A CHIM rooms build stops at the content fingerprint: it requires maps/<room>.bsp after the room became maps/<room>.chim
- [IMAGE-ROOM-MAPS-LATE-PASSES-48](IMAGE-ROOM-MAPS-LATE-PASSES-48.md): Image checks after the CHIM rooms install skip CHIM rooms: entity tracker 47 cells against 52, dressing 81 pieces against 99, actor contact 0 placements against 93
- IMAGE-ROOM-MAPS-OPTIMIZER-RECEIPT-48 (no report page): A CHIM rooms build stops at the map optimizer check: the room maps are staged but not in the optimizer receipt
- IMAGE-ROOM-MAPS-SKIP-PASSES-48 (no report page): CHIM rooms were installed before the image passes that write a room worldspawn, so CHIM room maps would miss interior sky, hand metadata and cell numbers

Related bugs in other categories:

- ARRIVAL-LONG-FRAME-DEV6-59 (no report page): Arriving in Seyda Neen, the first frame of play lasts about 13 to 15 seconds; v0.0.59-dev6 test sessions stopped on it as a stall
- [CONTAINER-STRIP-TAKE-STALL-59](CONTAINER-STRIP-TAKE-STALL-59.md): A take or put in the container strip can hold the game for seconds
- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [HEART-CHAMBER-LOAD-HANG-62](HEART-CHAMBER-LOAD-HANG-62.md): The game stops on the Loading screen when teleporting to the heart chamber, with the music still playing
- IMAGE-IDE-CYLINDER-TAIL-59 (no report page): On the emulated A1200 IDE port the last 144 sectors of the world partition AW_WORLD0 were unreadable, so loading Khuul stopped the game
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [SMOKE-DELIVERY-OLD-COPY-58](SMOKE-DELIVERY-OLD-COPY-58.md): The playtest delivery ran an old copy of the boot smoke: the v0.0.58 release smoke failed four times on a working image

<!-- END GENERATED CATEGORY -->
