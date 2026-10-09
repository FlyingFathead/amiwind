# Quick test builds

A normal build makes everything a release ships. When you only want to test
one thing (a door, a town, the dialogue of one area), you can leave whole
groups of content out and get a playable image sooner. Such an image is a
**quick test build**: the game, the receipts and the image name say so, and it
never matches a release.

<!-- contents start -->
## Contents

- [Leaving content out: `--exclude`](#leaving-content-out---exclude)
- [Only what the area references: `--exclude-unreferenced`](#only-what-the-area-references---exclude-unreferenced)
- [MiniWind builds are quick test builds by default](#miniwind-builds-are-quick-test-builds-by-default)
- [How you can tell a quick test build](#how-you-can-tell-a-quick-test-build)
- [What release builds refuse](#what-release-builds-refuse)

<!-- contents end -->

Quick test builds are for development versions only (a `VERSION` such as
`0.0.33-dev1`). Release candidates and finals refuse every exclusion; see
[What release builds refuse](#what-release-builds-refuse).

## Leaving content out: `--exclude`

```sh
./build.sh --data-files "/path/to/Morrowind" --exclude video,music
```

`--exclude` takes one or more group names, separated by commas, and can be
given more than once. Every group also has its own readable option; these two
commands do exactly the same:

```sh
./build.sh --data-files "/path/to/Morrowind" --exclude video,voice
./build.sh --data-files "/path/to/Morrowind" --exclude-video --exclude-voice
```

The older switches still work and mean the same groups: `--no-npc-gallery` is
`--exclude npc-gallery`, `--no-harvest` is `--exclude harvest`.

### The groups

| Group (option) | What the builder skips | Typical time saved | What the game does without it |
| --- | --- | --- | --- |
| `video` (`--exclude-video`) | The videos of the media stage and the intro movie | about 1 minute of media-stage work (17 videos, 104 MB), plus about 6 s for the intro movie (37 MB) | New Game goes straight to the prison ship, with no black wait. The console says `This build was made without the intro movies (quick test build).` `playvid` says the same. |
| `music` (`--exclude-music`) | The music stage; the image gets no soundtrack | about 7 s, plus the soundtrack copy (56 MB less on the disk) | Silence where music would play. One console line at startup, and one when the opening music would start. |
| `voice` (`--exclude-voice`) | The recorded dialogue library (`Sound/Vo`, 6,447 files) | about 2 minutes 20 s of media-stage work, 192 MB less on the disk | The dialogue library is left out. NPC greetings and the ship's intro lines are kept, so the opening scene still runs. One console line at startup. |
| `npc-gallery` (`--exclude-npc-gallery`) | The NPC gallery stage (every NPC and creature as an inspection model) | about 30 minutes on 4 workers and 233 MB on the disk: the longest stage of a full build, and the open-world stages wait for it | `dbg npcgallery` and the other gallery commands say the build has no gallery. Every NPC of the game is still built. |
| `interiors` (`--exclude-interiors`) | The Seyda Neen and Balmora room compiles | part of the scene chain: the Balmora rooms stage took 135 s without its rooms (4 workers, busy machine) against a median of 319 s with them (8 workers); Seyda Neen's rooms are compiled in the same stage that places the town's residents, which still runs | The house doors of both towns say `Area unavailable`. The prison ship and the Census and Excise Office stay, so a new game still starts normally. |
| `harvest` (`--exclude-harvest`) | The harvest stage and its image pass | a few seconds of the stage, plus the image pass | Mushrooms stay in the world as scenery (same shape, same collision) but cannot be picked. |
| `unreferenced` (`--exclude-unreferenced`) | Content the built area does not reference | area builds only; see [below](#only-what-the-area-references---exclude-unreferenced) | Only what the area shows is built. |

The times are measured on 4 workers, with other work running on the same
machine at the same time; they show the size of the saving, not a promise. The
media stage and the NPC gallery run beside the scene stages, so a saving there
shortens the build most when the machine has few cores free.

### What stays in every build

Dressing (hooks, ropes, ferns, lanterns), clutter, props, trees, grass, reeds,
rocks and every other placed object with collision stay in **every** build,
quick or not. NPCs can get stuck on them, so tests of walking, paths and
collision need them. `--exclude dressing`, `--exclude flora` and similar names
are refused with the reason. The separate debugging switches
`--skip-dressing` and `--no-tree-sprites` still exist, but they are not
exclusion groups.

The shared engine assets that maps and the engine find by name, not by a
placement, are **always included** too: the shared exterior sky
(`gfx/aw_shared_sky.lmp`, which every exterior map names in its `_aw_sky_mode`
and `_aw_sky_asset` keys), the palette and colour map, `gfx.wad`, the console
fonts and background, the game font, the menu, user interface and logo
graphics, the startup logo, the game code and the start-up settings. No
exclusion group and no `--exclude-unreferenced` list may drop them; the image
step of every quick test build checks them (and the sky's size) and stops with
the names of any that are missing. The check is recorded in
`always-included.json` beside the image.

## Only what the area references: `--exclude-unreferenced`

`--exclude-unreferenced` works in **area builds**: builds that make one area
instead of the whole game. In a full build every area is built, so everything
is referenced; the builder refuses the option there.

The builder follows the area's references:

- the built cells and everything placed in them;
- the records those placements use, and leveled lists, all the way down;
- each NPC's race, class, faction, head and hair, the body parts of their race
  and sex, their clothing, armour and other inventory;
- the scripts of all of these, and every object those scripts name;
- every script that names one of the built cells (a script may bring an actor
  or an item there later), with everything it names.

Anything it cannot resolve is kept and listed in the receipt; nothing is
dropped silently. Every placed object stays, dressing included. Music is never
trimmed: `--exclude music` is the only way to leave it out.

You can name the groups it trims (default: all of them):

| Group | What it trims |
| --- | --- |
| `npcs` | NPC and creature records the area does not place or script. The NPC gallery then holds exactly the included NPCs and creatures. |
| `voice` | Recorded lines no included NPC or creature can ever say. Every line in their dialogue pool stays: greetings, topics, idles, hellos, combat lines, persuasion. A line is kept when one included actor matches its speaker, race, class, faction, sex and cell conditions. Conditions that depend on the running game (functions, variables) never drop a line. Lines a script plays with `Say` are kept. |
| `sounds` | Sound effects that only left-out records use. A sound nothing names stays. |
| `models`, `textures` | Listed in the receipt only: the scene stages of an area build already convert only what the area places. |

Examples, one per group:

```sh
# Everything the area does not reference (all groups):
--exclude-unreferenced
# Only the speech audio: just the lines the area's NPCs can say:
--exclude-unreferenced voice
# Only the NPC gallery: exactly the area's NPCs and creatures:
--exclude-unreferenced npcs
# Only the sound effects:
--exclude-unreferenced sounds
# Receipt only (nothing is dropped by these two yet):
--exclude-unreferenced models,textures
# Several at once:
--exclude-unreferenced voice,npcs,sounds
```

### What the receipt shows

The builder writes the area's list to `reference-closure.json` in the run
folder, and `build.json` keeps the summary:

- the built cells;
- counts: records, NPCs, creatures, body parts, models, voice files, voice
  lines kept and left out, sound files left out;
- the included NPC and creature IDs, the body parts, the voice files;
- `kept_by_script`: what was kept because a script may need it, and which
  script;
- `unresolved_kept`: names that point to no record, kept.

Measured on the owner's own game files, for Balmora (its 9 exterior cells and
43 interiors):

| | Full build | Balmora only |
| --- | --- | --- |
| NPC gallery records (NPCs and creatures) | 2,935 | 191 (132 NPCs, 59 creatures) |
| NPC gallery on the disk | 233 MB | 18 MB |
| NPC gallery stage, 4 workers | about 30 minutes in recent full builds | about 9 minutes from an empty model cache (267 models) |
| Voice files | 6,447 (186 MB converted) | 4,158 (121 MB converted) |
| Sound files left out | 0 | 189 (15 MB) |

Balmora's exterior alone: 75 gallery records and 1,701 voice files (57 MB).

Converting the voices takes time in proportion to their number: on a quiet
machine with 4 workers the whole voice library took about 2 minutes 20 s, so
Balmora's 4,158 files save roughly 50 s of the media stage, its exterior's
1,701 files roughly 1 minute 20 s (an estimate from the measured totals; the
area runs were measured on a busy machine and are not compared).

## MiniWind builds are quick test builds by default

A MiniWind build (`--miniwind`) leaves the videos out and keeps only the voices
and NPC records Balmora references, as if you had added

```sh
--exclude video --exclude-unreferenced voice,npcs
```

Music stays, every line the included NPCs can say stays, and the shared sky and
the other always-included assets stay. `--with-video` keeps the videos;
`--exclude-unreferenced none` keeps the whole voice library.

## How you can tell a quick test build

- The image name ends in `-quick-test` (for example
  `AmiWind-v0.0.33-dev1-quick-test.hdf`).
- The boot volume holds `QUICK-TEST-BUILD.txt` with the list of what was left
  out and what the game does without it.
- `build.json`, `build-state.json` and `build-summary.json` have an
  `excluded_content` block; the summary prints
  `Content: quick test build, excluded: video, music`.
- In the game, the console says at startup:
  `Quick test build, made without the intro movies and the music.`
- The game reads the list once from `id1/excluded-content.txt`. A complete
  build has no such file and shows no message.

The stage cache knows about exclusions: a stage that a group changes gets a
different fingerprint, so a later `--reuse-from` never mixes a quick test
stage into a complete build. Stages no group touches keep their fingerprint
and can be reused.

## What release builds refuse

Release candidates (`0.0.33-rc1`) and finals (`0.0.33`) are always complete.
The builder stops before any work when such a version is combined with:

- any `--exclude` group or its `--exclude-...` option;
- `--no-npc-gallery` or `--no-harvest` (they are exclusion groups too);
- `--exclude-unreferenced`.

The image step checks the same again on its own. The other release rules
(build from scratch, no private waivers) are in the
[Linux build guide](../../LINUX_BUILD.md).
