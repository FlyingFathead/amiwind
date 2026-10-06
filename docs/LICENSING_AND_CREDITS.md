# Licensing, provenance and credits

**Last updated:** 6 October 2026 (Europe/Helsinki).

**All AmiWind code is free and open source under the GNU General Public
License (GPL), using the component-specific versions described below.**

AmiWind's host tools and original 68000 runtime are GPL-3.0-only. The separate
`engine/aga/` program additions and QuakeC are GPL-2.0-or-later; the selected
AmiQuake port is built and distributed under GPLv2. These programs exchange
asset files and do not link OpenMW or the GPLv3 host code into the Amiga binary. Preserve copyright notices,
licence texts and modification history when incorporating third-party code;
include the applicable corresponding source/build material with distributed
binaries. A credit alone is not a replacement for licence compliance.

Original Morrowind and Kickstart assets remain separately licensed. Owning the
game and converting it locally does not relicense its assets under the GPL.
The public source package contains source, tools, documentation and selected
development screenshots and short clips for documentation. Playable images
containing converted game assets are private local build outputs; a private
checkpoint does not grant a public redistribution licence for its art, audio
or ROM.

## Public source notice

**No original game assets or ROMs are redistributed with AmiWind's public
source releases.** The GPL applies to the code under its applicable notices;
it does not grant rights to original or converted game assets, music, voices,
ROMs or Workbench files. Copyright remains with the respective contributors
and rights holders. See also the [AmiWind FAQ](FAQ.md#do-i-need-my-own-morrowind-files-what-is-included-in-the-release).

The AGA runtime incorporates elements of id Software's Quake and the AmiQuake
lineage, modified, extended and adapted for AmiWind. These components are
distributed under GNU GPL version 2, with the applicable original copyright and
licence notices retained. Individual v2-or-later grants remain intact.
This is permitted source-code reuse under those licences, not a claim that
Quake's commercial game assets are free to redistribute. Copyright in upstream
work remains with its respective contributors. AmiWind modifications do not
transfer their copyrights or replace their licence terms.

No id Software or Bethesda game assets, Commodore/Cloanto ROM bytes or Workbench
files are included in the public source package. It contains no compiled
AmiWind executable. The upstream assembly identified as recovered from the
NovaCoder binary is excluded from the selected build and corresponding-source
package; independent C2P and GPL C span routines are used instead. The historical checksum-pinned upstream archive contains those files; the
current checkout contains only the previously reviewed corresponding-source
selection and builds directly from it without downloading that archive.

The engine can be compiled without game files or a Kickstart ROM. Converting
the demo requires the user's Morrowind installation. Emulator playback requires
the user's suitable licensed ROM; physical hardware supplies its own firmware.
Neither the GPL nor this fan-tribute notice grants rights in converted assets,
sound recordings, trademarks or ROMs. The project is independent and is not
endorsed by Bethesda/ZeniMax, id Software, Commodore, Cloanto or OpenMW.

## Renderer adoption review, 27 September 2026

| Source | Observed licence/provenance | Current decision |
| --- | --- | --- |
| OpenMW | Repository declares GPLv3; review individual reused files/dependencies | Suitable candidate for a GPL host exporter; current converters are standalone; opening captures and reference checks run OpenMW externally, with no OpenMW source bundled |
| id Software Quake | Inspected engine headers grant GPL v2 or later | Reusable engine foundation under applicable GPL terms; preserve id Software notices |
| terriblefire/AmiQuake | README declares GPLv2 for port additions; inherited `r_main.c`, `d_scan.c`, `vid_amiga.c` headers say v2 or later | Review selected modifications before combining with GPLv3-only code; keep a separately licensed runtime option |
| `src/c2p8.s` and `src/d_scan_68k.s` in that fork | Comments identify code extracted from NovaCoder's v1.36 binary; README asserts GPL compliance | Excluded from the AmiWind release build; independent C2P and GPL C spans are selected |
| PyFFI | External Niftools dependency, package classifier identifies BSD licence | Not vendored; retain its licence if a later tool bundle distributes it |

GPLv2-only and GPLv3 code should not be treated as interchangeable. The
v2-or-later permission permits selecting a later version for those files, but
that does not automatically settle separate contributors' additions. Host tools
and Amiga executables exchanging documented asset files can be developed as
separate programs with their respective notices. Revisit compatibility if code
is combined into one program. The source package includes the complete selected engine tree; `engine/aga/qc/defs.qc`
retains id Software's field ABI declarations and copyright notice. Complete
corresponding runtime source must accompany distributed runtime binaries.

Inspected AmiQuake revision: `9c62d905151614af3e788ae3145a0d4ecc8a7bb8`.
OpenMW music reference: `46bd4599203ee52ffc0f3e8edb3fc159a0303a49`,
`files/data-mw/scripts/omw/music/music.lua` and `helpers.lua`. These describe
playlist selection and shuffled orders. The 68000 playlist implementation is
original project code; no Lua source is included.

## Acknowledgements

Created by **FlyingFathead a.k.a. Horstator**. Thanks to **ChaosWhisperer**.

- Bethesda Softworks and the Morrowind creators for the original game. Jeremy
  Soule for its soundtrack. Purchase the original from [GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition)
  or [Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).
- The OpenMW contributors for the open engine, content loader, documentation
  and the host rendering used for the opening captures.
- id Software, including John Carmack, and the Quake source contributors.
- Peter McGavin (Amiga video driver), NovaCoder (AmiQuake), and Stephen Leary
  (the terriblefire GCC port), for the upstream Amiga engine lineage adapted
  here. The selected source and excluded binary-derived assembly are described
  above; this acknowledgement does not claim reuse of the excluded routines.
- Timo Heimonen for the Hunter 68060 performance-patch study.
- The Niftools/PyFFI developers for the external static-model reader.
- vasm, amitools and FS-UAE contributors for the separately installed build and
  validation tools. These acknowledgements do not imply endorsement.

## Primary references

- [OpenMW source](https://github.com/OpenMW/openmw) and [licence](https://github.com/OpenMW/openmw/blob/master/LICENSE).
- [Quake source](https://github.com/id-Software/Quake), [licence](https://github.com/id-Software/Quake/blob/master/gnu.txt) and [source/data notice](https://github.com/id-Software/Quake/blob/master/readme.txt).
- [Reviewed AmiQuake revision](https://github.com/terriblefire/amiquake/tree/9c62d905151614af3e788ae3145a0d4ecc8a7bb8).
- [GNU GPL version-compatibility guidance](https://www.gnu.org/licenses/gpl-faq.html#v2v3Compatibility).
- [Niftools/PyFFI](https://github.com/niftools/pyffi).
- [Hunter 68060 performance study](https://github.com/timoheimonen/amiga-hunter-performance-68060).

## Host build tools

External tools recorded for AGA development include the pinned AmigaPorts GCC SDK,
ericw-tools 0.18.1 (GPLv3 host tools), id Software Quake-Tools qcc (GPLv2-or-later),
fast-simplification 0.2.0 (MIT), SciPy (BSD), and NumPy (BSD). They are not linked
into the Amiga runtime. The default readable interface glyphs are original AmiWind 5x7 bitmap designs
in an 8x8 atlas. The unchanged optional retro atlas is generated locally from
the host DejaVu Sans Mono font. No Amiga ROM/system font is extracted and no
Quake artwork is bundled. Keep dependency notices if distributing tools. Exact reference versions
and their verification scope are maintained in [build dependencies](BUILD_DEPENDENCIES.md).

## Proposed bundled QCC

The [third-party compiler plan](THIRD_PARTY_COMPILERS.md) records the pinned
GPL-2.0-or-later QCC source, licence/notices, proposed provider selection and
corresponding-source requirements. QCC remains a separately installed host tool in the current dev4/RC1 build
pipeline. Fresh setup can fetch the pinned, hash-checked source and build a
managed compiler; later builds reuse it, and `--qcc` can select an external
compiler. The proposed bundled source/provider is not implemented, and no
QCC source or compiler binary is included in the public source package. See
the [bootstrap implementation](../tools/fetch_native.py).

---

[Project overview](../README.md) · [FAQ](FAQ.md) · [Build dependencies](BUILD_DEPENDENCIES.md)
