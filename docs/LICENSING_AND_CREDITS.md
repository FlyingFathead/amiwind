# Licensing, provenance and credits

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Public source notice](#public-source-notice)
- [The CHIM engine (from v0.0.33)](#the-chim-engine-from-v0033)
- [Project decision: upstream AmiQuake assembly, 10 October 2026](#project-decision-upstream-amiquake-assembly-10-october-2026)
- [Renderer adoption review, 27 September 2026](#renderer-adoption-review-27-september-2026)
- [Acknowledgements](#acknowledgements)
- [Primary references](#primary-references)
- [Host build tools](#host-build-tools)
- [Proposed bundled QCC](#proposed-bundled-qcc)

<!-- contents end -->

**Last updated:** 16 October 2026 (Europe/Helsinki).

**All AmiWind code is free and open source under the GNU General Public
License (GPL). Different parts use different GPL versions, as described below.**

AmiWind is made of two programs with two licences. The tools that run on your
PC (the converter and the builder) and the original 68000 runtime are under
GPL-3.0-only. The Amiga engine program additions in `engine/aga/` and its
QuakeC game code are under GPL-2.0-or-later, and the AmiQuake port they build
on is built and distributed under GPLv2. The two programs never share code:
the PC tools only write the asset files that the Amiga engine reads. Neither
OpenMW nor the GPLv3 host code is linked into the Amiga binary.

If you reuse any of this code, keep the original copyright notices, licence
texts and change history, and include the matching source and build material
when you share binaries. The GPL asks for that, and a credit line alone is not
enough.

The original Morrowind assets and the Kickstart ROM have their own licences.
Owning the game and converting it on your own machine does not put its assets
under the GPL. The public source package holds source code, tools,
documentation, and a few development screenshots and short clips used in the
documentation. Playable disk images contain converted game assets, so they are
private build outputs that stay with whoever built them. A private test build
does not give anyone the right to share its art, audio or ROM.

## Public source notice

**AmiWind's public source releases contain no original game assets and no
ROMs.** The GPL covers the code, as stated in each file's notice. It gives no
rights to original or converted game assets, music, voices, ROMs or Workbench
files. Copyright stays with the respective contributors and rights holders.
See also the [AmiWind FAQ](FAQ.md#do-i-need-my-own-morrowind-files-what-is-included-in-the-release).

The Amiga runtime contains parts of id Software's Quake and of the AmiQuake
port, changed and extended for AmiWind. These parts are distributed under GNU
GPL version 2, with their original copyright and licence notices kept in the
files. Files that were granted under "version 2 or later" keep that grant. The
licences allow this reuse of source code; they do not make Quake's commercial
game assets free to share. Copyright in the upstream work stays with its
contributors, and AmiWind's changes do not take over that copyright or replace
its licence terms.

The public source package contains no id Software or Bethesda game assets, no
bytes from Commodore or Cloanto ROMs and no Workbench files. It also contains
no compiled AmiWind executable. The default build uses AmiWind's own
chunky-to-planar (C2P) routine and GPL C span routines. The upstream assembly
that was recovered from NovaCoder's AmiQuake binary has been in the source tree
since 10 October 2026, but only the experimental `upstream` engine profile
links it (see the [project decision](#project-decision-upstream-amiquake-assembly-10-october-2026)
below). The checkout builds directly from its own source tree; it does not
download the historical, checksum-pinned upstream archive.

The engine compiles without any game files and without a Kickstart ROM.
Converting the game needs your own Morrowind installation. Playing in an
emulator needs a suitable, licensed Kickstart ROM; a real Amiga uses its own
firmware. Neither the GPL nor this fan-project notice gives rights to converted
assets, sound recordings, trademarks or ROMs. AmiWind is an independent project
and is not endorsed by Bethesda/ZeniMax, id Software, Commodore, Cloanto or
OpenMW.

## The CHIM engine (from v0.0.33)

AmiWind runs on the CHIM engine. It is built on GPLv2 code from id Software's
Quake (John Carmack and the id team) and from its Amiga port AmiQuake (Peter
McGavin, NovaCoder, Stephen Leary). The CHIM builder, which converts your own
Morrowind files, is under GPLv3.

- **What CHIM is:** AmiWind's overhauled engine. In many places it is a
  rewrite of the original AmiWind engine, and it still uses parts of Quake and
  the AmiQuake port. The main change is how the world is kept: every asset is
  stored once, placed by reference and streamed in around the player, instead
  of loading one self-contained map at a time. See [CHIM engine](chim/README.md).
- **Licence:** the CHIM engine is an adaptation (a derivative work) of that
  GPL code and is distributed under GNU GPL version 2. Files whose notices say
  "version 2 or later" keep that grant. The complete source is in `engine/aga/`.
- **Notices:** every original copyright notice (id Software, the AmiQuake
  authors) stays in the files. The public history of this repository records
  each change, and the [changelog](CHANGELOG.md) summarises them.
- **Two programs:** the GPLv2 engine and the GPLv3 builder and host tools are
  separate programs that only exchange files; neither is linked into the
  other. The licence notes above apply to both.
- **Names:** "built on Quake code" describes where the code comes from; it is
  not a brand. Quake is a trademark of id Software. Nothing here implies
  endorsement by id Software, the AmiQuake authors, Bethesda Softworks or
  ZeniMax. "CHIM" is a word from Morrowind's lore, used here as the name of a
  free fan engine.

## Project decision: upstream AmiQuake assembly, 10 October 2026

AmiWind follows upstream AmiQuake's own licence reading for its 68k assembly.
Upstream states that the port and every file in it are GPL v2 "as per original
Quake source code license". NovaCoder's AmiQuake is a port of GPL Quake, and
upstream publishes the routines recovered from its v1.36 binary as readable,
commented source. This decision replaces the 27 September 2026 exclusion
described below.

Five files are concerned: `d_scan_68k.s`, `d_scan_68k_nofpu.s`,
`mathlib_68k.s`, `c2p8.s` (credited to NovaCoder's original AmiQuake,
recovered and ported by Stephen Leary) and `fixedpoint_asm.s` (Stephen Leary).
Each one is measured against AmiWind's C code before it ships. They keep their
GPL v2 terms and notices, and the C code stays selectable
([ENGINE-UPSTREAM-ASM-UNUSED-36](bugs/ENGINE-UPSTREAM-ASM-UNUSED-36.md)).

Since 10 October 2026 the five files are in the source tree. Only the
experimental `upstream` engine profile links them
([ENGINE_PROFILES.md](ENGINE_PROFILES.md)); the default `c` profile links none
of them:

| File in `engine/aga/src` | Credit | Linked by the `upstream` profile |
| --- | --- | --- |
| `c2p8.s` | NovaCoder's original AmiQuake chunky-to-planar routine, recovered and ported by Stephen Leary | yes |
| `d_scan_68k.s` | NovaCoder's original AmiQuake span routines, recovered and ported by Stephen Leary | yes (its turbulent span loop) |
| `d_scan_68k_nofpu.s` | Stephen Leary, after NovaCoder's FPU version | the 68020 build only |
| `fixedpoint_asm.s` | Stephen Leary | the 68020 build only |
| `mathlib_68k.s` | NovaCoder's original AmiQuake maths routine, recovered and adapted by Stephen Leary | no (selectable) |

Each file starts with a header that names upstream AmiQuake (TerribleFire's
GCC port), the file and the revision
`9c62d905151614af3e788ae3145a0d4ecc8a7bb8`. Below the header the text is
upstream's, except for five lines marked `AmiWind:` in the two span files;
those lines assemble to the same machine code.

## Renderer adoption review, 27 September 2026

This table records the review as it was made on 27 September 2026. Its last
row was later replaced by the project decision above.

| Source | Observed licence/provenance | Current decision |
| --- | --- | --- |
| OpenMW | The repository declares GPLv3; reused files and dependencies are reviewed one by one | A suitable candidate for a GPL host exporter. The current converters are standalone. Opening captures and reference checks run OpenMW as a separate program; no OpenMW source is bundled |
| id Software Quake | The inspected engine headers grant GPL v2 or later | A reusable engine foundation under the applicable GPL terms; the id Software notices are kept |
| terriblefire/AmiQuake | The README declares GPLv2 for the port's additions; the inherited `r_main.c`, `d_scan.c` and `vid_amiga.c` headers say v2 or later | Selected changes are reviewed before they are combined with GPLv3-only code; a separately licensed runtime option is kept |
| `src/c2p8.s` and `src/d_scan_68k.s` in that fork | Comments say the code was extracted from NovaCoder's v1.36 binary; the README states GPL compliance | Excluded from the AmiWind release build; AmiWind's own C2P and GPL C spans are used instead. **Superseded 10 October 2026** (project decision, above) |
| PyFFI | An external Niftools dependency; its package classifier names the BSD licence | Not vendored; its licence goes with it if a later tool bundle distributes it |

GPLv2-only code and GPLv3 code are not interchangeable. The "v2 or later"
permission allows a later GPL version to be chosen for those files, but that
does not settle the licence of other contributors' additions. Host tools and
Amiga programs that only exchange documented asset files can be developed as
separate programs, each with its own notices. If code is ever combined into one
program, compatibility has to be checked again. The source package includes the
complete selected engine tree; `engine/aga/qc/defs.qc` keeps id Software's
field ABI declarations and copyright notice. Distributed runtime binaries must
come with their complete corresponding runtime source.

Inspected AmiQuake revision: `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`.
OpenMW music reference: `46bd4599203ee52ffc0f3e8edb3fc159a0303a49`,
`files/data-mw/scripts/omw/music/music.lua` and `helpers.lua`. These files
describe how OpenMW picks playlists and shuffles their order. The 68000
playlist code is original project code; no Lua source is included.
OpenMW 0.51 script compiler and sound code (`components/compiler`, `apps/openmw/mwscript`,
`apps/openmw/mwsound`), read for the rules of MWScript (argument kinds, the scanner's
tolerances, junk after `else`, unknown variables) and the sound distance rule. AmiWind's
MWScript compiler (`tools/mwscript/`) and interpreter (`engine/aga/src/aw_mwvm.c`) are
original project code; no OpenMW source is included ([MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md)).

## Acknowledgements

Created by **FlyingFathead a.k.a. Horstator**. Thanks to **ChaosWhisperer**.

- Bethesda Softworks and the Morrowind creators for the original game, and
  Jeremy Soule for its soundtrack. The original is available from
  [GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition)
  and [Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).
- The OpenMW contributors for the open engine, the content loader, the
  documentation and the host rendering used for the opening captures.
- id Software, including John Carmack, and the Quake source contributors.
- Peter McGavin (Amiga video driver), NovaCoder (AmiQuake) and Stephen Leary
  (the terriblefire GCC port), for the upstream Amiga engine that AmiWind
  adapts. Which of their source files AmiWind uses, including the upstream
  assembly, is described above.
- Timo Heimonen for the Hunter 68060 performance-patch study.
- The Niftools/PyFFI developers for the external static-model reader.
- Arseny Kapoulkine for [meshoptimizer](https://github.com/zeux/meshoptimizer)
  (MIT). Its mesh simplifier (v1.3, `src/simplifier.cpp`, `src/allocator.cpp`,
  `src/meshoptimizer.h`) is vendored unchanged in `third_party/meshoptimizer`
  with its licence. It is compiled on the build host and used by the CHIM mesh
  method `meshopt+merge` ([mesh methods](chim/MESH_METHODS.md)). It is a host
  build tool; nothing of it is linked into the Amiga runtime.
- Michael Garland and Paul S. Heckbert, "Surface Simplification Using Quadric
  Error Metrics" (SIGGRAPH 1997), the method behind AmiWind's own
  boundary-locked reducer; and Stefan Hertel and Kurt Mehlhorn's convex
  partition, the method behind AmiWind's own planar merge. Both are AmiWind
  implementations, not copies.
- The vasm, amitools and FS-UAE contributors for the build and validation
  tools, which are installed separately. None of these acknowledgements implies
  endorsement.

## Primary references

- [OpenMW source](https://github.com/OpenMW/openmw) and [licence](https://github.com/OpenMW/openmw/blob/master/LICENSE).
- [Quake source](https://github.com/id-Software/Quake), [licence](https://github.com/id-Software/Quake/blob/master/gnu.txt) and [source/data notice](https://github.com/id-Software/Quake/blob/master/readme.txt).
- [Reviewed AmiQuake revision](https://github.com/terriblefire/amiquake/tree/9c62d905151614af3e788ae3145a0d4ecc8a7bb8).
- [GNU GPL version-compatibility guidance](https://www.gnu.org/licenses/gpl-faq.html#v2v3Compatibility).
- [Niftools/PyFFI](https://github.com/niftools/pyffi).
- [Hunter 68060 performance study](https://github.com/timoheimonen/amiga-hunter-performance-68060).

## Host build tools

The Amiga build uses these external tools: the pinned AmigaPorts GCC SDK,
ericw-tools 0.18.1 (GPLv3 host tools), id Software's Quake-Tools qcc
(GPLv2-or-later), fast-simplification 0.2.0 (MIT), meshoptimizer 1.3 (MIT,
vendored, see above), SciPy (BSD) and NumPy (BSD). None of them is linked into
the Amiga runtime. Anyone who distributes these tools keeps their licence
notices with them.

The default interface glyphs are original AmiWind 5x7 bitmap designs in an 8x8
atlas. The optional retro atlas is generated, unchanged, on the build machine
from the DejaVu Sans Mono font installed there. No Amiga ROM or system font is
extracted, and no Quake artwork is bundled. The exact reference versions, and
how far each one has been verified, are listed in
[build dependencies](BUILD_DEPENDENCIES.md).

## Proposed bundled QCC

The [third-party compiler plan](THIRD_PARTY_COMPILERS.md) records the pinned
GPL-2.0-or-later QCC source, its licence and notices, the proposed way of
providing it, and what corresponding source would have to ship with it. Today
QCC is still a separately installed host tool in the dev4/RC1 build pipeline.
A fresh setup can fetch the pinned, hash-checked source and build a managed
compiler, which later builds reuse; `--qcc` selects an external compiler
instead. The proposed bundled source is not implemented yet, and the public
source package contains no QCC source or compiler binary. See the
[bootstrap implementation](../tools/fetch_native.py).

---

[Project overview](../README.md) · [FAQ](FAQ.md) · [Build dependencies](BUILD_DEPENDENCIES.md)
