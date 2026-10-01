# AmiWind release workflow

Official project: https://github.com/FlyingFathead/amiwind/

Use one shared release number. The current candidate is **v0.0.24-rc4**.
The owner published v0.0.24-rc3 at commit `0d13122`; v0.0.23 remains the
stable release. Stable v0.0.24, titled **Welcome to Balmora**, requires owner
approval after RC playtesting. Earlier archives and tags remain immutable.
`VERSION` is the maintained version source for Python metadata, native build
includes, runtime/boot strings, receipts, presets and package filenames.

## Deliverables and structure

| Archive | Structure and purpose |
| --- | --- |
| `AmiWind-v0.0.24-rc4-public-source.zip` | Complete repository under `amiwind/`. |
| `AmiWind-v0.0.24-rc4-from-rc3-source-patch.zip` | Added/changed public files and patch metadata, from the exact published RC3 source ZIP. |
| `AmiWind-v0.0.24-rc4-private-playable.zip` | Matching HDF, supplied ROM, launcher, presets and private evidence under `AmiWind-v0.0.24-rc4/`, following the delivered RC3 wrapper. |

Each ZIP has a same-name `.sha256` sidecar. Only the two source archives and
their checksums belong in GitHub release assets. No private playable, ROM or
converted game assets may be included. Asset-free dry runs do not replace the
playable HDF verification.

The source repository has one root. Native AGA code is in `engine/aga/`, host
conversion code in `src/mwad/`, commands in `tools/`, documentation in `docs/`,
presets in `resources/emulators/`. Only core files and README belong at the root.
Keep compiled output in ignored `out/` or a chosen external workspace. Preserve
previous methods, fonts, hand variants and release archives.

## Incremental updates

The exact base is `AmiWind-v0.0.24-rc3-public-source.zip`, SHA-256
`0c4978995c0e2d6540cc57e6bb0183fa20dc8e73c1a8b087417c6b5ed494623e`.
`docs/PATCH-v0.0.24-rc4.json` records the base, changed paths and removals.
Verify a clean application reproduces every file in the full source ZIP,
including the package manifest. The two RC3 screenshots also require their
explicit `.gitignore` exceptions; source checks now enforce that alongside the
media allowlist. Unzip does not delete obsolete files; apply
only explicitly listed removals. Protect existing local changes first.
Always provide the full source archive alongside the incremental.

## Release gate

**ALWAYS CHECK FOR TRAILING WHITESPACE BEFORE POSTING AN AUTOMATED PUSH/PUBLISH
SCRIPT.** Check all delivered files before posting or packaging. This check
belongs to package preparation, before the owner downloads or applies anything.
Passing tests and an archive allowlist do not replace it.

`tools/release.py --check`, candidate creation and candidate validation all reject
trailing spaces/tabs, whitespace-only lines, space-before-tab indentation and
blank lines at EOF in new or modified text files. Only byte-identical historical
base files are exempt; the current patch's base hashes identify them. This also
covers files that are untracked or extracted without Git metadata. Before
delivery, additionally run `git diff --no-index --check BASE_TREE CANDIDATE_TREE`
on clean extracted source trees and retain the result. Keep the owner's
`git diff --check` as a final check, not the first place defects are discovered.

Candidates are written under `incoming/`, checked independently, then promoted
into immutable `releases/`. Validate ZIP paths, source allowlist, content hashes,
patch application, private image/ROM hashes, corresponding source and boot
behavior. Never overwrite a released ZIP or relabel an old executable as a new
build. Keep historical version strings in historical records accurate.

Update README, project state, changelog and validation notes before packaging.
Report the tests actually run and their limits. Public CI compiles without game
files or ROMs. Full conversion, Windows/WSL and physical Amiga behavior require
their own validation. The owner runs Git/GitHub commands; see FIRST_RELEASE.md
for the historical first-release workflow. The source repository and source
releases are public. Playable images, converted game files and supplied ROMs
remain private and must never become GitHub release assets.

## Boot identity

NPC placement is a release gate: follow [NPC_GROUND_CONTACT.md](NPC_GROUND_CONTACT.md)
on fresh scene loads, sub-cell/door re-entry and save restoration. Keep original
reference IDs in the report, investigate non-grounded residents and document
intentional airborne/scripted exceptions. A floor correction is not proof that
the final packaged runtime passes the audit.

Transition experiments follow the numbered-method protocol in
[PERSISTENCE_AND_STREAMING.md](PERSISTENCE_AND_STREAMING.md): preserve current
method 1, measure loading phases and heap separately, and compare any new method
2 before making it a default. Do not replace the existing loader during research.


Normal preflight and dry-run screens display their shared AmiWind version. The
preflight also repeats the version in its pass/fail footer so screenshots always
identify the runtime under test. Guest-visible hardware is reported by
`AmiWindCheck`; FS-UAE-only settings are validated by the portable host launcher.
The boot identity also includes:

```text
By FlyingFathead
https://github.com/FlyingFathead/amiwind/
Special thanks to: ChaosWhisperer
```

Public source excludes original/converted game data, reusable extracted fonts,
ROMs and private images. The explicitly allowlisted owner-approved README screenshots are a
documentation exception. Preserve component licence notices and keep complete
development recovery sets separate from playable packages.

Public documentation and release assets use generic example paths. Keep owner
usernames, machine names and local directory layouts in private handoff material.

## Amiga limitations

### Legacy filesystem names: 30 bytes per component

The RC1 HDF build rejected `scene-doors-bmhlaalucouncil.txt`: 31 ASCII
characters/bytes exceed the selected legacy Amiga OFS/FFS limit of **30 bytes
for each filename or directory component, including the extension**. A name
that works in the host workspace can therefore fail during Amiga packaging.
This is a constraint of our legacy target format; do not assume that newer
Amiga filesystems or a host-directory emulator mount behave identically.

Use stable abbreviations, shorthands, numbering or bounded identifiers when
needed. Reserve room for prefixes, suffixes and extensions. Do not silently
truncate: different originals can then collide. Keep target names ASCII where
possible, case-insensitively unique, and independent of display labels.

The door converter now emits `doors-bmhlaalucouncil.txt` (25 bytes). Runtime
loading prefers `doors-<map>.txt` and retains the older-name fallback. The
payload preflight `tools/amiga_fs.py:check_payload_names` runs before HDF
packing and rejects overlength components, unsupported characters and
case-insensitive path collisions. Validate the complete staged payload, not
only the examples that originally failed.

### Traceable original-to-target mapping

Every shortening must retain a reverse lookup. `config/seyda_area.json` and
`config/balmora_interiors.json` keep original cell names beside stable runtime
map IDs. `tools/prepare_doors.py` additionally generates private
`asset-name-map.json`: source master SHA-256, original cell, runtime map ID,
BSP path, current/previous door-bank filename, and each original door's record
ID, placed reference number, cell/grid, mesh path and destination. RC1 has
60 scene entries and 185 placed door records. Keep exact source spellings;
never replace them with the shortened target name.

| Original Morrowind cell | Runtime map | Generated door bank |
| --- | --- | --- |
| Balmora, Hlaalu Council Manor | `bmhlaalucouncil` | `doors-bmhlaalucouncil.txt` |
| Balmora, Caius Cosades' House | `bmcaius` | `doors-bmcaius.txt` |
| Balmora, Guild of Mages | `bmmages` | `doors-bmmages.txt` |

That JSON covers scene/BSP and door-bank naming. Other asset families retain
source-to-output receipts: `balmora-interiors.json` links NPC record IDs,
appearance part meshes and authored greeting paths to hashed MDL/WAV names;
`door-audio.json` links source samples and hashes to short WAV names. Original
placed geometry and transforms remain in `interior-reference.json`, while
room conversion reports identify selected meshes. These are complementary
records, not a claim that a single JSON covers every texture and sound in the
game. Keep the reports with private conversion evidence and include new asset
families as they are introduced. A one-to-many conversion must list every
output; reused outputs must preserve every relevant source identity.

For recurrence: trace the rejected path to its converter; choose a stable
short name; update producer and consumer together; emit the mapping; run the
payload preflight; rebuild the HDF; read files back and boot the packed image.
Do not fix only a local staging copy or rely solely on a host-directory boot.

## RC2 diagnostic snapshot boundary

The owner requested an interim v0.0.24-rc2 while the stricter contact audit and
model-budget investigation remain open. Its separate snapshot receipt explicitly
records a failed production placement gate (23 findings); no audit row is removed.
`build_aga.py image` still stops on those findings. Do not promote this snapshot
as a passed final build. Retain payload/readback hashes, source/binary receipt,
full failed audit and native evidence in the private package. The ordinary source
allowlist and whitespace checks still apply. Publish only public-source archives
and their checksums, using the prerelease flag; never publish the playable HDF,
ROM, model catalogue, converted assets or private inspection reports.

## Palette and skin-tone consistency

Before packaging, run `ui_palette.sync_lookups(game, check=True)` against the
final game directory. The production image builder enforces this check. Palette
reservation must update the dependent lighting and fog columns, including when
reopening a previously converted payload. Retain the resulting table hashes in
the private receipt. Use a pale-skinned resident as a native visual sentinel;
check both nearby daylight and normal world lighting/fog. See the
[ashen-face investigation](IMPLEMENTATION_JOURNAL.md#j027--pale-faces-mapped-back-to-sky-grey).
This catches colour-table drift; it does not certify every face or texture seam.

## RC3 recovery candidate boundary

The owner requested RC3 before the final grounding work is complete. Retain the
same diagnostic boundary as RC2: full source, matching private playable image,
failed placement audit and independent HDF readback. A complete gallery does not
turn the remaining 23 contact findings into a passed production gate. Source
checks and targeted native tests still apply. Publish as a prerelease.
