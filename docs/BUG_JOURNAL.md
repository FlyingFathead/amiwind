# Bug journal

## CI-HOSTDEPS-30: host CI job failed on the first v0.0.30 push, 7 October 2026

The hosted `host-launcher-parity` job failed: flame extraction asked for the
NIF reader for a synthetic non-NIF test model, and that job installs only
numpy and Pillow. Not tagged or released. Repaired in source; the host tests
now also run in a reduced environment before every handoff.
[Report](bugs/CI-HOSTDEPS-30.md).

## v0.0.30-rc1 owner playtest summary, 7 October 2026

WinUAE playtest by the owner: Census office interiors work
(CENSUS-ENTITIES-30 accepted), mushroom picking on the road to Balmora works,
Balmora works and torches work. Open from the same playtest, all WinUAE music
crackles or pauses at transitions: AUDIO-NEWGAME-30, AUDIO-03,
AUDIO-ENTER-29, AUDIO-APPEARANCE-29, AUDIO-LOAD-29. Character attributes and
the papers reader (no disk loads) stay clean.

## CENSUS-ENTITIES-30: owner-accepted in v0.0.30-rc1, 7 October 2026

Owner WinUAE playtest of v0.0.30-rc1: the Census and Excise Office interiors
work. Same playtest: small music clicks on the pier at head selection and on
Choose/OK (AUDIO-APPEARANCE-29) and small crackles entering the Census office
(AUDIO-LOAD-29); both open.

## AUDIO-NEWGAME-30: rc1 playtest audio reports, 7 October 2026

v0.0.30-rc1 WinUAE playtest by the owner: music crackles when confirming New
Game (new, [report](bugs/AUDIO-NEWGAME-30.md)); crackles as the game fades in
after the intro (AUDIO-03); a split-second pause on Enter to follow the guard,
which worked in earlier versions (AUDIO-ENTER-29, regression); heavy crackling
from the ship's hull to the deck (AUDIO-LOAD-29). All open; tracked for after
v0.0.30.

## CENSUS-ENTITIES-30: misplaced objects in the Census and Excise Office, 7 October 2026

1. Symptom (v0.0.30-dev5 playtest): an upright rug on the upper floor whose
   lower half shows as a black hole in the ceiling below, and a tapestry
   inside a bookshelf. The fireplace and its flames are correct.
2. Cause: the dev5 lighting rebuild kept an older object list (v0.0.29) on
   top of geometry from the dev3 rebuild, which had added one object. Every
   later object pointed at its neighbour's model: 67 of 140.
3. Introduced in v0.0.30-dev5; dev4 was correct. Only the Census map; the
   rebuilt Temple's numbering matches.
4. Fix: the dev4 object list plus dev5's flames; all 140 objects point at the
   same models as in dev4, and the geometry is unchanged. The rebuild step now
   stops if any object's model number differs from the rebuilt geometry.
5. Shipped in v0.0.30-rc1. [Details](bugs/CENSUS-ENTITIES-30.md).

## SEYDA-LOAD-HANG-30: rare freeze during a Seyda Neen region load, 7 October 2026

1. Symptom: in about 5 of 70 automated FS-UAE runs of the Seyda Neen test
   route the game stopped during a region load; the screen froze and quit was
   ignored. Not yet reported in manual play.
2. Reproduction: scripted route seyda-east-y-300 under FS-UAE 3.1.66 with the
   console debugger; v0.0.30-dev4 and dev5 engines.
3. Evidence: every CPU sample was the idle loop. The game task waited on the
   DOS signal inside a read (`fread` -> dos.library `Read` -> exec `Wait`); its
   reply port was empty and the file-system handlers were idle.
4. Cause: open. A read request or its reply was lost below the engine (file
   system handler or emulator disk layer); not an engine loop.
5. Not tied to host disk load: 0 freezes in 12 runs with a 4 GB copy running.
6. Status: open, no fix. Next: name the calling engine function and check the
   emulator log at the moment of the freeze.
7. Shipped: present in v0.0.30 if it is a real game fault.

## BUILD-SEYDA-REGEN-30: public build cannot regenerate Seyda Neen, 7 October 2026

Reproduced 7 October 2026: running the partition on the original v0.0.29 inputs
stops with the message below. `build_aga.py image` calls the Seyda partition
without a canonical terrain source while `config/terrain-visual-cull.json`
enables culling by default, so the partition stops with "Enabled Seyda culling
requires --canonical-land-source". The shipped sub-cells were finished by
terrain steps outside the repository; v0.0.29 reused them unchanged. Next:
bring the missing steps into the public build.

## INTRO-ROLES-30: crash on a region change, 7 October 2026

`NUM_FOR_EDICT: bad pointer` on a Seyda Neen sub-cell load. The opening
sequence kept actor pointers across a map reload; one pointed past the new
entity list. Repaired by validating role pointers before use. Scripted route:
dev3 crashed 2/2, repaired engine 0/3. [Details](bugs/INTRO-ROLES-30.md).

## CONVERTER-ROOT-ROTATION-30: same cause in more maps, 7 October 2026

The root-rotation converter bug behind the Temple also turned Velothi kit walls
in Tharys Ancestral Tomb (see-through holes) and `in_nord_fireplace_01` in five
Seyda Neen interiors (fireplace facing away). All six maps are rebuilt; only
the root-rotated meshes changed. One Balmora exterior placement is pending.
[Details](bugs/CONVERTER-ROOT-ROTATION-30.md).

## BALMORA-TEMPLE-GEOMETRY-29: cause found, 7 October 2026

The Temple's missing and edge-on walls, see-through holes and floating objects
come from the scenery converter applying each mesh's NIF **root node rotation**.
Morrowind ignores that rotation (it keeps root translation and scale), and the
Velothi kit pieces carry a 90-degree root yaw, so they were turned a quarter
turn. Earlier audits compared geometry flattened by the same converter and
could not see it. Candidate repair: ignore the root rotation in
`model_geometry`; regression `tests/test_scenery_root_transform.py`. The
rebuilt Temple matches OpenMW at the reported views in FS-UAE; only the five
root-rotated models changed. Other converted maps with root-rotated meshes:
Tharys Ancestral Tomb and the fireplace interiors. Not shipped; first fixed
version pending. [Details](bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

Entries before 7 October 2026 are in
[the v0.0.29 bug journal](journals/BUG_JOURNAL-v0.0.29.md).
