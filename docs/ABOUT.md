# About AmiWind, licences and credits

_Last updated with AmiWind v0.0.46 (20 October 2026)._

Credits, the Morrowind edition AmiWind is tested against, and the licence summary that used to be on the README front page. The full details per component: [licensing and credits](LICENSING_AND_CREDITS.md).

Created by **FlyingFathead a.k.a. Horstator**
Thanks to: **ChaosWhisperer**

> Massive thanks to everyone in the Amiga community who have been willing to
> share code and ideas to make this dream come true to a beloved platform.
> *May the wind be on your back!*

A fan-made tribute, free and open-source conversion tools, and an experimental
Amiga runtime. The growing playable world combines an island-wide terrain/scenery pass with
detailed starting towns, while much of Morrowind's gameplay remains unfinished. The A500 experiment
is preserved alongside the accelerated AGA development track.
**Official project repository:** [FlyingFathead/amiwind](https://github.com/FlyingFathead/amiwind).
**Repository root: `amiwind/`.** This directory contains the conversion tools,
complete native engine source, tests and documentation. `engine/aga/` is part of
this repository, not a second repository. See [repository layout](REPOSITORY_LAYOUT.md).

**Original Morrowind game files are required. You must provide your own copy.**

> **AmiWind recommends the GOG GOTY edition of Morrowind.**
>
> AmiWind has been developed and tested primarily against the GOG Game of the Year
> release. The GOG installation includes additional loose TrueType (TTF) font assets
> that provide a better starting point for AmiWind's offline font conversion and
> rasterization.
>
> The Steam GOTY edition does not normally include these loose TTF font assets. When
> they are unavailable, AmiWind will fall back to Bethesda's original `.fnt` + `.tex`
> bitmap fonts and continue the build. This fallback is supported, but converted font
> quality and appearance may differ and may be inferior, particularly when fonts must
> be rendered at sizes different from the original bitmap assets.
>
> **For the best-tested and preferred AmiWind conversion path, use the GOG GOTY edition:**
>
> https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition

The Steam GOTY edition remains a supported fallback input when its required game data
passes AmiWind's validation.

AmiWind runs on the CHIM engine, built on GPLv2 code from **id Software's
Quake** (John Carmack and the id team) and its Amiga port **AmiQuake** (Peter
McGavin, NovaCoder, Stephen Leary). The CHIM builder that converts your own
Morrowind files is GPLv3.

The Amiga runtime contains code from **id Software's Quake** and the
**AmiQuake** port, changed and extended for **AmiWind**. That code is
distributed under the **GNU GPL version 2**, with the original copyright and
licence notices kept in the files; files granted under "version 2 or later"
keep that grant. AmiWind's host tools and the original A500 runtime are a
separate program under **GPL-3.0-only**; see [LICENSE](../LICENSE). OpenMW serves
as a reference for file formats and behaviour. The current converters are
standalone tools and include none of its code; earlier opening experiments used
OpenMW only to make external captures. [Licensing and credits](LICENSING_AND_CREDITS.md)
has the details for each component.

Licensed Amiga ROMs are available from
[Cloanto / Amiga Forever](https://www.amigaforever.com/), which is worth
supporting. The public repository includes no Kickstart ROM, so you need a
suitable one of your own. Public test records identify the tested ROMs by
checksum.

Setup works much as it does in OpenMW: you point the tools at your installed
game folder. The conversion runs on your own machine and writes to a separate
workspace. AmiWind is an independent project, not an OpenMW release and not an
official Bethesda product.

> **Public source package: no commercial game data or ROMs.** The package
> includes no Quake or Morrowind game data, reusable game artwork, music,
> voices, game executables, Amiga Kickstart ROMs or Workbench files. It holds
> a selection of development screenshots and a short clip for the
> documentation, but no compiled AmiWind executable. The default engine build
> links no assembly recovered from a game binary (see
> [licensing and credits](LICENSING_AND_CREDITS.md) for the upstream
> assembly used by an experimental profile). The GPL-licensed engine source is
> separate from the game assets. Converting the data needs your own Morrowind installation, and
> running the result in an emulator needs a suitable licensed Kickstart ROM.
> Compiling only the engine needs neither.

Copyrights stay with their holders, including the original code contributors,
and each component keeps its own licence. Morrowind, The Elder Scrolls, Quake,
Amiga and related names belong to their owners. AmiWind is an independent fan
tribute, not affiliated with or endorsed by Bethesda/ZeniMax, id Software,
Commodore, Cloanto or the OpenMW project. The GPL gives no right to share game
assets or ROMs. Game images you build yourself are private build outputs, not
public source releases.

Thanks to the Morrowind creators, the Amiga community, and the contributors whose
work made this experiment possible. The earlier A500 track, previous methods,
fonts and hand-rendering alternatives remain available in the source and history.
