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
exclusions and character already chosen. The table is
`config/miniwind-presets.json`; the builder makes one option per preset.

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
| `opening-ship` (`--miniwind-opening-ship`) | Opening ship: lantern and ship lighting check | exterior scope, starts in `interior:Imperial Prison Ship`, no NPC gallery, shows the quick character screen |

The description is the startup screen's `Scene:` line. Options you give
yourself win over the preset's (for example `--miniwind-description`).
Presets are refused for release candidates and finals, like every MiniWind
build.

The `vivec-arena-pit` preset stops before any stage with the start point's
message until the Vivec Arena interiors are converted
(IMPORT-TOWN-NO-INTERIORS-32); see the
[worked example](DIRECT_START.md#worked-example-the-vivec-arena-pit).

### Adding a test spot

Add a row to `config/miniwind-presets.json`:

```json
{
  "name": "balmora-council-club",
  "description": "Council Club: talk test",
  "scope": "full",
  "start": "interior:Balmora, Council Club",
  "exclude": [],
  "unreferenced": "voice,npcs",
  "character": "Dark Elf,Battlemage,Ilmeni",
  "skip_census": null
}
```

| Key | Meaning |
| --- | --- |
| `name` | lower case letters, digits and hyphens; the option becomes `--miniwind-<name>` |
| `description` | the startup screen's `Scene:` line (printable ASCII, two lines at most) |
| `scope` | `full` or `exterior` |
| `start` | a `--direct-to-game-map` start point, or `null` for Balmora's arrival point |
| `exclude` | quick-test groups (`video`, `music`, `voice`, `npc-gallery`, `interiors`, `harvest`) |
| `unreferenced` | `--exclude-unreferenced` groups: `"all"`, a comma list, or `null` for none |
| `character` | a `--quick-character` value, or `null` for the Hors preset |
| `skip_census` | `true`, `false`, or `null` for the default (on unless a character is given) |

The builder checks every row with the same rules as the options
(`tests/test_miniwind_presets.py`), so a bad row fails the tests before
anyone builds with it.

Back to the [CHIM build guide](README.md).
