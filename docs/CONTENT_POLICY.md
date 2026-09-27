# Original game content stays outside this repository

This is an unofficial fan tribute and proof-of-concept porting pipeline.
Original Morrowind files are required and must be supplied by the user. Please
support the original work by purchasing it from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).

The source repository and its checked source archive contain project code,
configuration, documentation, five selected development screenshots and synthetic
test generators. The screenshots illustrate development and are not reusable
runtime assets. The archive does not contain
id Software or Bethesda game files, extracted assets, converted game assets,
Amiga ROMs, Workbench files or compiled AmiWind executables. Selected GPL Quake
engine code is included as source; it is not Quake game data. The complete corresponding
runtime source under engine/aga also excludes binary-recovered assembly.
The original game and its assets belong to their respective rights holders.
This project is not affiliated with or endorsed by Bethesda or the OpenMW team.

The OpenMW comparison concerns the user-supplied-data setup model. This project
does not claim OpenMW compatibility and does not bundle OpenMW or Hunter code.

## Repository and external workspace

| Location | Purpose | Included in source archive? |
| --- | --- | --- |
| `amiwind/` | Our source, tests and documentation | Yes, explicit file list |
| Existing Morrowind installation | User's original files | No |
| `morrowind-amiga-workspace/original/` | Optional separate local copy of originals | No |
| `morrowind-amiga-workspace/generated/` | Terrain, placements, reduced assets, dialogue output | No |
| `morrowind-amiga-workspace/previews/` | Game-derived images and future audio auditions | No |
| `morrowind-amiga-workspace/cache/` | Intermediate extraction/conversion data | No |
| `morrowind-amiga-workspace/build/` | Future native objects/binaries and measurements | No |
| `morrowind-amiga-workspace/incoming/` | Candidate source archives | No |
| `morrowind-amiga-workspace/releases/` | Validated immutable source archives | No |

External workspaces remain supported. The guided builder now defaults to ignored
`amiwind/out/`; this directory is excluded from all source packages. Converted
sprites, terrain, textures and audio remain private build outputs. The owner
selected five specific screenshots for README documentation; only those named
PNG files are approved in the source packager. Their contents are not covered
by the project code licence.

Path checks reject private inputs/outputs beneath distributable source paths,
including symlink routes; ignored out/ is the designated local-work exception. The source-release checker uses an
explicit file list, refuses unexpected files and source symlinks, and checks
archive contents against the source bytes. `.gitignore` is an additional guard,
not the release selection mechanism. Review new source-file additions before
adding them to the approved list.

## OpenMW integration boundary

The current capture script runs a separately installed OpenMW on the host. No
OpenMW executable or source is copied into this source ZIP. OpenMW identifies
its licence as GPLv3; its FAQ separately requires users to supply Morrowind data.
A future modified OpenMW baker or reused engine code must retain the applicable
licence/notices and meet corresponding-source obligations when distributed.
Audit dependencies and individual file notices before that integration ships.
The engine licence does not grant redistribution rights to Bethesda's assets.

Apart from the five selected README screenshots, public packaging excludes
derived screenshots, sprites, terrain packets,
PCM/MP3 audio, game databases/archives, game executables and Kickstart bytes as
well as the originals. Private build archives are never public release inputs.
Calling a project a tribute or requiring ownership does not itself grant asset
redistribution rights. The host tools and original A500 runtime are
GPL-3.0-only; the separate AmiQuake-derived AGA runtime is distributed under
GPLv2. See [licensing and credits](LICENSING_AND_CREDITS.md), the root LICENSE
and `engine/aga/COPYING`. These grants cover code, not Morrowind/Quake assets or ROMs.

References: [OpenMW repository](https://github.com/OpenMW/openmw),
[OpenMW FAQ](https://openmw.org/faq/),
[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html).

This is a fan-made proof of concept by a Morrowind enjoyer. Please support
[Cloanto / Amiga Forever](https://www.amigaforever.com/) for licensed ROMs,
and purchase Morrowind from the GOG or Steam links above. Existing legitimate
copies can be supplied locally. No game or ROM download mechanism is provided.

## Asset-free test image

CI_DRY_RUN.md documents the separate public test image. It contains compiled
engine/notice code and original notice text, with no game assets, ROM or
Workbench files. Its ZIP includes corresponding source and licence notices.
The normal game-containing image remains private. Neither .gitignore nor a
filename alone is the publishing rule: the source allowlist and explicit
asset-free artifact paths are checked separately.
