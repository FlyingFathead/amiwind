# MiniWind playtest builds

A MiniWind build is a quick partial-area test of Balmora on the CHIM engine,
for development versions only. The build type itself (`--miniwind`,
`--miniwind-scope full|exterior`, `--miniwind-description`, the startup screen
and the image marking) is described in
[MiniWind playtester build](../../MINIWIND_PLAYTESTER.md).

The overview (what MiniWind is for, the presets, console and automation) is
[MiniWind: the test ground](../../MINIWIND.md).

## What every MiniWind build adds

- **A quick test build by default.** A MiniWind build leaves the videos out and
  keeps only the voices and NPC records Balmora references (as with
  `--exclude video --exclude-unreferenced voice,npcs`); music, every line the
  included NPCs can say and the shared sky stay. `--with-video` and
  `--exclude-unreferenced none` turn this off. Details:
  [Quick test builds](QUICK_TEST_BUILDS.md#miniwind-builds-are-quick-test-builds-by-default).
- **A start point.** `--direct-to-game-map` starts in a room or at a spot of
  Balmora instead of its arrival point; the startup screen's `Scene:` line
  then names it. Details: [Start straight in the game](DIRECT_START.md).

## Presets

A preset is a named test spot: a MiniWind build with its scope, start point,
exclusions and character already chosen. Each preset is a build recipe in
`config/recipes/miniwind/` ([Build recipes](../../BUILD_RECIPES.md)); the
builder makes one option per preset.

```sh
./build.sh --data-files "/path/to/Morrowind" --miniwind-preset list
./build.sh --data-files "/path/to/Morrowind" --miniwind-balmora-exterior
./build.sh --data-files "/path/to/Morrowind" --miniwind-preset balmora-exterior
```

| Preset (option) | Scene | What it builds |
| --- | --- | --- |
| `balmora` (`--miniwind-balmora`) | Balmora: exterior and interiors | today's MiniWind: the Balmora exterior on CHIM and its rooms |
| `balmora-exterior` (`--miniwind-balmora-exterior`) | Balmora exterior (map only) | the Balmora exterior only; every door says `Area unavailable` |
| `vivec-arena-pit` (`--miniwind-vivec-arena-pit`) | Vivec Arena Pit: combat test | starts in `interior:Vivec, Arena Pit`, no NPC gallery, only what the room references |
| `vivec-arena-chim` (`--miniwind-vivec-arena-chim`) | Vivec Arena on CHIM: arrival, walkways, frame edge | Vivec on CHIM stage A: starts at the Arena's arrival point (`vivec_arena`), the Arena exterior and its rooms, no NPC gallery; the start makes it a Vivec Arena build (no `--miniwind-town` needed) |
| `opening-ship` (`--miniwind-opening-ship`) | Opening ship: lantern and ship lighting check | exterior scope, starts in `interior:Imperial Prison Ship`, no NPC gallery, shows the quick character screen |

The description is the startup screen's `Scene:` line. Options you give
yourself win over the preset's (for example `--miniwind-description`).
Presets are refused for release candidates and finals, like every MiniWind
build.

The `vivec-arena-pit` preset builds the Vivec Arena (its start picks the
town) with its rooms (`chim-rooms-vivec_arena`) and starts inside the Pit
(`vai000`); see the
[worked example](DIRECT_START.md#worked-example-the-vivec-arena-pit).

### Adding a test spot

Add a recipe file to `config/recipes/miniwind/`, named after the preset
(`balmora-council-club.json`):

```json
{
  "schema": "build-recipe-1",
  "name": "balmora-council-club",
  "description": "MiniWind preset --miniwind-balmora-council-club: Council Club: talk test",
  "options": {
    "miniwind": true,
    "miniwind_scope": "full",
    "miniwind_description": "Council Club: talk test",
    "direct_to_game_map": "interior:Balmora, Council Club",
    "exclude_unreferenced": "voice,npcs",
    "quick_character": "Dark Elf,Battlemage,Ilmeni"
  },
  "inputs": [],
  "written_with": null,
  "checked_with": null,
  "status": "unverified"
}
```

| Field | Meaning |
| --- | --- |
| `name` | lower case letters, digits and hyphens, the file name; the option becomes `--miniwind-<name>` |
| `options.miniwind` | `true` |
| `options.miniwind_description` | the startup screen's `Scene:` line (printable ASCII, two lines at most) |
| `options.miniwind_scope` | `full` or `exterior` |
| `options.direct_to_game_map` | a `--direct-to-game-map` start point; left out: Balmora's arrival point |
| `options.exclude` | quick-test groups as one comma list (`video`, `music`, `voice`, `npc-gallery`, `interiors`, `harvest`) |
| `options.exclude_unreferenced` | `--exclude-unreferenced` groups: `"all"` or a comma list; left out: none |
| `options.quick_character` | a `--quick-character` value; left out: the Hors preset |
| `options.skip_census` | `true` or `false`; left out: the default (on unless a character is given) |
| `options.miniwind_boot` | dbg console commands run once on arrival, separated by `;` |

The builder checks every preset with the same rules as the options
(`tests/test_miniwind_presets.py`), so a bad preset fails the tests before
anyone builds with it. Before v0.0.36 the presets were rows of one table
(`config/miniwind-presets.json`); every recipe gives exactly the options its
row gave (`tests/test_build_recipe.py`).

Back to the [CHIM build guide](README.md).
