# AmiWind release workflow

Official project: https://github.com/FlyingFathead/amiwind/

Published checkpoint: **v0.0.26-rc1**, recording native Windows build/game-entry
success with experimental support. Current candidate: **v0.0.26**, adding the
Docker builder and private input/export helper. Final-version full conversion,
export and WinUAE game entry passed locally. Hosted Docker, Linux and Windows
CI must pass for the exact publication commit. Known gameplay issues remain
documented; a source release is
not a claim that the complete Morrowind game has been implemented or playtested.
The owner performs all Git/GitHub publishing.

## Historical rc1 handoff (published)

The following describes the completed rc1 handoff. Its tag is immutable;
final v0.0.26 must use its own snapshot, checksums, exact-commit CI evidence
and release artifacts. Require Docker, Linux and Windows jobs to pass for
the final pushed commit. Retain complete failed-step logs before stopping,
and perform whitespace checks before commit and against the exact commit.

The complete rc1 public-source ZIP contains every allowlisted source file and
its generated package manifest. The separate private transfer kit contains the
overlay/publishing helpers and checksums; do not upload that private kit.
Overlay only after checking the exact cloned v0.0.25 base commit and preserving
local work. Run Linux checks before publication. Push main from the publishing
host and require a successful source-check workflow for that exact commit before
creating the annotated v0.0.26-rc1 tag and a GitHub **prerelease**. Do not replace
existing tags or mark this candidate as the latest stable release. Upload only
the validated public-source ZIP and its checksum.

## Historical v0.0.25 complete update package

`AmiWind-v0.0.25-complete-update.zip` contains the complete public source ZIP,
a source patch from rc10, updater, checksums and apply/recovery/publish scripts.
The public source ZIP contains every maintained file under `amiwind/` plus a
generated package manifest. No private playable, HDF, game payload or ROM is
included. Only source ZIPs, updater and checksums are uploaded to GitHub.

Finish the current build before applying to the rc10 checkout. APPLY.sh verifies
the complete kit, updates changed files with an external backup and validates
the result against the complete source package. Overlapping local edits stop
before writes; unrelated edits remain preserved and require review before exact
release validation. Existing rc10 cache entries remain compatible. Recovery uses
the same workspace/cache and retains the original completed rc3 terrain/music.

PUBLISH.sh stages the source allowlist, commits, pushes main and waits for a
successful `source-check.yml` run whose `headSha` equals that exact commit. It
then creates the annotated `v0.0.25` tag and a regular GitHub release (not a
prerelease), downloads the uploaded assets and verifies their checksums and tag.
Existing tags are never replaced. The owner runs the supplied Bash commands.

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

### FFS partition capacity and hardfile capacity are different

For the current Kickstart 3.1 / DOS1 FFS compatibility profile, plan partitions
**below 2 GiB** and keep the complete device's addressed range **below 4 GiB**.
One RDB `.hdf` can contain several such partitions; a 2 GiB partition bound is
not a 2 GiB limit on the complete multi-partition hardfile. Verify the actual
ROM, filesystem and device path, including native reads at the highest used
offsets. These planning bounds do not certify arbitrary physical controllers.

The older `build_aga.py` **1 GiB boot-partition cap was a project build setting**,
not the FFS format limit. Do not describe it as an Amiga filesystem restriction.
Keep that smaller boot partition only when its payload fits; use the available
partition capacity deliberately when building the combined terrain image.

Measure the converted runtime payload before deciding its disk layout. Original
Morrowind installation size is not the converted-image size: overlapping BSPs
duplicate terrain, collision and visibility tables, and converted audio/textures
have different storage costs. Record payload bytes, partition sizes, free-space
allowance and highest used device offset in the build receipt. Check avoidable
duplication before expanding storage. Distinguish decimal GB from binary GiB
(2 GiB = 2,147,483,648 bytes). See [storage profiles](STORAGE.md).

### Preferred partition contents and performance

If capacity eventually requires two larger partitions, prefer **partition 1 for
the main Morrowind game**, including frequently visited interiors and shared
resources, plus boot files, configuration and saves. Prefer **partition 2 for
future Bloodmoon/Tribunal content, videos and less frequently used assets**.
Move selected base-game interiors only if needed; shops, guilds and quest hubs
are not inherently rare. Keep expansion assets together for play within that
expansion, and retain one copy of shared resources.

This is the owner's future placement preference. The present v0.0.25-rc1 image
uses two 1,664 MiB partitions with base-game terrain balanced between them; no
expansion conversions are included. Its measured payload exceeds one 2 GiB
partition, so further reductions or selective overflow are necessary before all
main-game content can occupy partition 1. Two exactly 2 GiB partitions plus RDB
space would exceed 4 GiB; keep both partitions and the complete image below their
respective planning bounds.

Two partitions do not cause operating-system swapping on the plain KS 3.1
baseline, and partition 2 in the same HDF has no inherent speed advantage.
Extra filesystem buffers/handler state consume RAM, and filesystem work costs
CPU time. Our current fallback search also checks primary paths before opening
second-volume files. Once open, reads use that file handle. A future direct
asset-to-volume index can avoid those failed lookups; it is not implemented.
Scene reloads may pause on either partition. Measure load time, RAM, frame stalls
and audio refill behavior before claiming a performance gain or no overhead.
See [content placement and costs](STORAGE.md#preferred-future-content-placement).

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

## v0.0.24 owner release decision - 1 October 2026

The owner explicitly requested the final v0.0.24 release after the RC4 delivery,
under the title **v0.0.24 - Welcome to Balmora (and Vvardenfell!)**. The 23 strict
contact findings remain known issues. Preserve their complete failed receipt;
never label them passed, remove rows or broaden tolerances to match release status.
The normal production image builder still stops on the audit. This milestone's
private assembly reuses the hash-verified RC4 converted content and freshly
builds the final-version runtime and preflight, then independently reads back
and tests the finished image. This explicit release decision is not a standing
permission to bypass future checks or hide new failures.

Public presentation must distinguish whole-island mapping from playable scene
coverage, and exclude Bloodmoon/Solstheim and Tribunal from that map's scope.
Fresh native captures need exact `.gitignore` exceptions and source allowlist
entries. The owner-run publisher verifies all expected public files are tracked
before committing; it creates a normal release, without the prerelease flag.
