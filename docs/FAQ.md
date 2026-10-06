# AmiWind FAQ

*Harry Horsperg's perspective as the project's author.*

**Last updated:** 2026-10-06 15:28:19 EEST (Europe/Helsinki, UTC+03:00). **FAQ revision:** 4.
**Published source baseline:** v0.0.29-dev4. **Latest stable release:** v0.0.28.
**In preparation:** v0.0.29-rc1, with the remaining checks and limitations in
the [release plan](PLAN-v0.0.29.md) and [RC1 issue tracker](BUGS-v0.0.29-RC1.md).

## What is possible on the Amiga?

That is the question driving AmiWind.

When the Amiga 500 came out, the Amiga already represented the future to me:
a beautiful multimedia machine that felt unique in its time. That feeling
continued with the A1200 and beyond. It is still part of why I want to create
for the Amiga.

Morrowind on the Amiga has always been a dream of mine. I love Morrowind, and I
love the Amiga. **I wanted to make that dream a reality for all Commodore Amiga
and TES III: Morrowind fans, and to see what we can optimize and make possible.**
Bringing the two together is the point of this project.

**It needs to be Morrowind, and it needs to be on the Amiga at the same time.**
The world, atmosphere and identity need to survive the journey, while the way
we represent and run them has to work within the Amiga's constraints.

AmiWind sits somewhere between a **conversion pipeline and a demake**. It is
also an optimization project in progress: the playable game gives us a demanding
world to work with, measure and improve. Finding out how far we can take it is
a central part of the project.

The code is **free and open source under the GPL**, with the applicable
versions explained below. I want this work to open doors for future Amiga game
developers and inspire more development across the **Motorola m68k family**.

Dreams can become working software. Then comes the work of making that
software fit, run better and reach less powerful machines.

**Because Morrowind is, and has always been, an otherworldly game title.**

**Morrowind ♥ Amiga ♥**

## Why build something so demanding before optimizing it?

My approach is to **"overdo" first, then optimize, optimize, optimize**.

**First, get all the assets in. Then optimize the compiler/conversion pipeline
and the runtime.** That is the overall development order.

We need the intended content in place so that we can map out what is there,
how it is represented and what it costs. Then we can use that complete content
baseline to work systematically on reducing the requirements. Individual
repairs and improvements already happen along the way; the larger optimization
phase follows the asset integration work.

Lower-spec Amigas are part of the plan. Once we have mapped out the content
and its costs, we will work on ways to bring that experience to less powerful
configurations. The current demanding development build gives us something
concrete to investigate and improve.

That means measuring several different things: geometry, memory, loading time,
rendering time, display conversion and storage. A slow scene is a problem to
understand and solve. Its current speed does not define the project's eventual
hardware requirements.

The intended progression is:

1. Get all the assets into the conversion pipeline and build the intended
   content baseline.
2. Measure where the work, memory and data go.
3. Change the representation or implementation to reduce those costs.
4. Check the result, including appearance and gameplay, and repeat on more
   constrained configurations.

The specific minimum machines and acceptable performance will be established
as those configurations are developed and tested. See the
[assemble-first optimization roadmap](ROADMAP.md#assemble-first-then-optimize-the-measured-world).

## How do non-destructive conversion, fallback paths and versioning fit in?

**My aim is to keep this non-destructive.** Preserve the original inputs and
earlier working representations, then produce new versions that we can compare,
select or fall back from. Trying a cheaper representation should leave us able
to return to the source and try a different approach.

We already have several alternative representations and fallback paths:

- Scenery uses both converted meshes and sprites, including different foliage
  representations in different areas.
- The first-person hands have a retained 3D path and an experimental sprite
  build option for a limited Nord unarmed prototype. A broader race/equipment
  catalogue captured with transparency from OpenMW is a new investigation,
  not a completed replacement. See [hand-rendering scope](FIRST_PERSON_HANDS.md).
- Sky resources have versioned formats and conversion revisions. The documented
  upgrade path backs up older night-sky data before replacing it, or retains it
  with a legacy warning when the necessary source textures are unavailable.

The [project overview](../README.md), [runtime options](AGA_RUNTIME.md) and
[sky resource documentation](DAY_NIGHT_AND_SKY.md) describe these existing
examples. Retained variants and versioned checkpoints give the optimization
work a baseline to return to; the broader range of target-specific choices
will grow as more content is integrated and measured.

If a lower-spec version ultimately needs a more **Daggerfall-like** presentation,
so be it. More sprites or simpler geometry may be part of finding a workable
balance while preserving Morrowind's world, atmosphere and gameplay.

**First, let us bring Morrowind across to the Amiga.** Then we can make those
decisions against the actual content and its measured costs, with the original
inputs and other representations still available.

## Why AGA graphics?

**Because I love AGA graphics. They are a big part of the Amiga feel I want
AmiWind to have.**

There is both a personal and a technical reason for keeping that target. AGA
gives the project a native Amiga display path with concrete constraints to work
against. Exploring what can be achieved within those constraints is part of
the attraction.

The chosen display, colours and performance tradeoffs are part of how Morrowind
becomes an Amiga experience. Retaining that character matters alongside making
the software faster. Additional display options can have value too; AGA is
central to the version I want to develop.

## Does real AGA hardware have enough graphics bandwidth for this?

AGA bandwidth is a real constraint. So are CPU speed, available memory,
visibility processing, texture access and loading costs. Their importance
depends on the actual scene, renderer and machine.

AmiWind's current native display defaults to **320 × 200 with 8-bit indexed
colour**. The CPU renders the 3D view in software. The native display path then
performs **chunky-to-planar conversion**, arranging the pixels into the
bitplanes that the Amiga chipset displays. See the
[video backend](../engine/aga/src/vid_amiga.c) and
[conversion routine](../engine/aga/src/aw_c2p.c).

At that resolution and depth, one complete image contains **64,000 bytes of
pixel data**, or **62.5 KiB**. More objects can make the scene much more expensive
to render, but they do not increase the size of that finished image. The world
and the renderer determine how much work is needed to produce it.

That arithmetic alone cannot establish a frame rate. Drawing and converting
the image, writing its bitplanes, display DMA and competing memory accesses
all have costs. Display data lives in Chip RAM, which the CPU shares with the
custom chips; other engine data can use Fast RAM. The
[AmigaOS documentation explains this memory distinction](https://wiki.amigaos.net/wiki/Programming_in_the_Amiga_Environment#Two_Kinds_of_Memory).

The practical answer will come from measuring particular real configurations
and optimizing their bottlenecks. The original PC game's complexity by itself
does not establish whether a converted scene is feasible. This is exactly the
question AmiWind's pipeline is meant to investigate.

## What hardware is the current version targeting?

The published development reference is an **accelerated AGA emulator
configuration**:

| Part | Current reference |
| --- | --- |
| Machine and chipset | A1200 / AGA / PAL |
| CPU and FPU | Emulated 68040 with FPU |
| Chip RAM | 2 MiB |
| Additional RAM | 16 MiB, configured as Zorro III memory in the emulator |
| CPU execution | JIT enabled, maximum emulated CPU speed |
| Default game display | 320 × 200, 8-bit indexed colour |

These settings are recorded in the
[FS-UAE preset](../resources/emulators/AmiWind-v0.0.29-dev4-FS-UAE.fs-uae),
[WinUAE preset](../resources/emulators/AmiWind-v0.0.29-dev4-WinUAE.uae) and
[AGA build guide](AGA_BUILD.md). The Zorro III setting describes the emulator's
memory configuration; it is not a specification for an ordinary A1200 expansion.

The standard engine build currently targets a 68040 and FPU, and the supplied
startup checker requires AGA and sufficient memory. A stock A1200 or stock A500
is therefore not a supported configuration for this build. The earlier A500
experiment remains in the repository, alongside the current accelerated AGA
track. See the [engine build settings](../engine/aga/Makefile),
[startup checker](../engine/aga/boot/bootcheck.asm) and
[project overview](../README.md#about-amiwind).

Bringing the experience down to lower specifications is planned work. A
particular physical accelerator, memory configuration or minimum frame rate
still needs its own measurements and validation.

## Can today's heavily upgraded Amigas realistically run AmiWind?

**Yes: the specifications and current CPU/FPU support provide a credible
hardware path, especially an A1200 with PiStorm32 Lite and a Pi 4 or CM4.**
This is a feasibility assessment from the hardware and source, with an actual
AmiWind hardware run still needed to establish compatibility and frame rates.

These are concrete configurations that retain Commodore AGA, checked against
project and builder documentation reviewed on **6 October 2026**:

| Configuration | CPU and memory available | Why it is a credible candidate |
| --- | --- | --- |
| A1200 + PiStorm32 Lite + Pi 4 or CM4 | Emu68 JIT with FPU support; the hardware project recommends a CM4 Lite with 2 GB RAM. Firmware and JIT reservations use part of that memory. | Supplies the CPU/FPU capabilities and substantially more memory capacity than the current development reference, while retaining AGA. |
| A1200 + TF1260 with a full 68060 | 128 MB Fast RAM; starts at 50 MHz, with firmware settings up to 100 MHz subject to the fitted CPU and stability. | A physical FPU-equipped 68060 and ample Fast RAM on a Commodore A1200. |
| A4000/A4000T + BFG9060 with full MC68060RC50 Rev. 6 | 128 MB Fast RAM; the builder documentation lists a 50 MHz default and optional 100 MHz operation for suitable Rev. 6 CPUs. | Another actual Commodore AGA platform with a full 68060/FPU and substantial memory. |

Sources: [PiStorm32 Lite hardware](https://github.com/PiStorm/pistorm32-lite-hardware/blob/main/README.md),
[TF1260 builder documentation](https://alen.dreamhosters.com/terriblefire/tf1260-info-and-installation/),
[BFG9060 builder documentation](https://gitlab.com/tkurbad/amiga-hardware-info/-/blob/master/BFG9060/README.md#technical-specification).
Higher 68060 clocks depend on the CPU and cooling. LC/EC versions lack the
full CPU's FPU; the physical 68060 configurations also require the appropriate
68060 system-support libraries.

The PiStorm case has specific source support. Emu68 identifies as a 68040 and
includes an automatically initialized support library. Its
[library initialization code](https://github.com/michalsc/68040.library/blob/1f1d0a492bcc695fa842f671885da953c890add3/src/init.c)
sets the 68040 and FPU flags that AmiWind's startup checker expects when the FPU
is present. Its [configuration documentation](https://michalsc.github.io/Emu68/Options.html)
also documents the FPU. The [hardware FAQ](https://pistorm.github.io/faq/hardware/)
currently identifies Pi 4/CM4 support; Pi 5/CM5 should not be assumed compatible.

The PiStorm project's [published benchmarks](https://pistorm.github.io/docs/benchmarks/)
include [CoreMark results](https://pistorm.github.io/assets/images/CoreMark.png)
and [DoomAttack through AGA](https://pistorm.github.io/assets/images/DOOM_Attack_AGA.png).
These provide context from other software and documented configurations.
CoreMark is an integer workload; the DoomAttack test specifies NTSC low
resolution. Neither is an AmiWind measurement or a direct prediction of its
frame rate, Chip RAM bandwidth or loading performance.

There is therefore a sound reason to pursue these machines. Extra installed
RAM does not automatically enlarge AmiWind's current **11 MiB game heap**,
defined in the [runtime allocation code](../engine/aga/src/sys_amiga.c), but it
provides room to develop larger budgets where useful. CPU rendering, AGA
presentation, loading and audio still need to be measured together on the
selected configuration.

## Why can AmiWind in FS-UAE run better than native OpenMW on a small PC?

On my smallest Linux NUC, I have observed AmiWind running better through
FS-UAE than OpenMW running natively. That is a useful observation about those
runs, even though it is not a controlled benchmark.

A converted game can require sufficiently less work that it remains faster
after the cost of emulation is added. AmiWind uses a reduced representation
and a low-resolution software renderer, and currently implements a smaller
set of game systems. OpenMW runs a different engine and workload. Resolution,
view distance, effects and scene settings can change the comparison further.

The observation supports investigating what the conversion and optimization
approach can achieve. It does not provide a direct conversion from NUC speed
to PiStorm or a physical 68060: their CPU execution, chipset access and I/O
costs differ. The way to find that relationship is to run the same AmiWind
scene on the actual target. See the [runtime scope](../README.md) and
[emulator configuration](FS-UAE-PLAYTESTING.md).

## Does running in WinUAE or FS-UAE prove real-hardware performance?

It demonstrates the native Amiga program running under the stated emulated
configuration. It also lets us inspect behaviour, reproduce problems and test
changes throughout development.

The current presets use JIT and maximum CPU speed. Selecting an emulated
68040 does not make the resulting frame rate a measurement of a physical
68040 at a particular clock speed. FS-UAE's own
[CPU-speed documentation](https://fs-uae.net/docs/options/uae_cpu_speed/)
distinguishes these execution modes.

**Physical-hardware performance remains to be established.** Useful results
need to identify the build, CPU or accelerator, memory, storage, display mode
and scene being measured. Emulator demonstrations are useful development
evidence; real-machine tests will establish what those machines can do.

## Why not use PiStorm32, RTG and MiniGL?

Those are useful possibilities to explore. They address different parts of
the problem:

| Technology | What it can change |
| --- | --- |
| PiStorm acceleration | The performance available for executing the Amiga program and its CPU workload. |
| RTG display | The framebuffer and display path. A suitable chunky display backend can avoid native AGA chunky-to-planar conversion. |
| MiniGL with a suitable 3D implementation | The rendering API and potentially the hardware doing the 3D drawing, for a renderer adapted to use it. |

RTG output and GPU-accelerated 3D rendering are separate capabilities. A
software renderer can use an RTG display while still drawing its polygons on
the CPU. Using MiniGL for that work requires an appropriate renderer
integration; installing a library alone does not change the existing
rendering code. See the [PiStorm RTG guide](https://pistorm.github.io/tutorials/p96setup/)
and the [PiStorm3D developer discussion](https://www.amigans.net/modules/newbb/viewtopic.php?post_id=162222).

AmiWind's inherited [video source](../engine/aga/src/vid_amiga.c) already
contains CyberGraphX/RTG paths. Their presence does not establish a validated
PiStorm/RTG release. The documented configuration and supplied startup checks
still target AGA, and the current renderer uses software drawing.

More CPU power or another display backend can expand the available budget.
Loading, memory use and gameplay systems still need their own work. AGA remains
a deliberate part of the project's identity while these additional avenues
can be investigated.

## Is this a Ship of Theseus question about what counts as an Amiga?

There is a Ship of Theseus question in heavily upgraded machines: how much can
change while we still regard the result as the same thing? A faster CPU,
different graphics hardware, replacement storage and a changed software stack
can each move someone's personal boundary.

For me, retaining AGA is a meaningful part of preserving the Amiga feel. It is
one of the things I want this particular project to keep as it develops.
That is a creative preference, and people can reasonably draw their own lines
elsewhere.

The same design question applies to the experience we are adapting: how much
can its representation change while it still feels like Morrowind? Recognizable
places, atmosphere and the intended gameplay matter. **Preserving Morrowind's
identity and the Amiga experience is the challenge.**

## Why start from AmiQuake?

**AmiQuake was the best available starting point I found for this project: an
existing, optimized Amiga 3D game engine with GPL-licensed source.**

It gave the project a practical foundation for software rendering and Amiga
integration, so development could concentrate on bringing over Morrowind's
world and building the conversion pipeline and runtime changes it needs.

The AGA runtime incorporates **id Software's Quake through the AmiQuake
lineage**, modified, extended and adapted for AmiWind. The conversion tools
prepare the original game data on the host; the Amiga runtime consumes the
converted output. OpenMW is a reference for formats and behaviour, and its
engine is not linked into the current Amiga program. See
[licensing, provenance and credits](LICENSING_AND_CREDITS.md).

**John Carmack ♥** And thanks to the other id Software and Quake contributors,
and to Peter McGavin, NovaCoder and Stephen Leary for the Amiga engine work
that helped make this starting point possible.

## Why not just run OpenMW under Linux on a PowerPC Amiga?

OpenMW is available in Linux repositories for some PowerPC architectures.
Those architecture names matter: for example,
[Debian's OpenMW package](https://packages.debian.org/sid/openmw) lists
64-bit PowerPC variants, which are not interchangeable with every older
PowerPC Amiga configuration. CPU, operating-system and graphics support
determine whether that route is usable on a particular machine.

**Even where it works, that would not fulfil the purpose of AmiWind.** I want
this retro Amiga adaptation: Morrowind's identity, an Amiga runtime, AGA's
character, and the work of finding what we can fit and optimize on these
machines. Turning the project into an OpenMW variant would change that goal.

OpenMW remains a valuable reference for formats and behaviour. AmiWind's own
conversion pipeline and Amiga runtime are how we are pursuing this particular
dream. See [project provenance](LICENSING_AND_CREDITS.md).

## What does the optimization pipeline actually work on?

There is work on both sides of the build.

The **host tools** convert and organize the source world, models, textures and
media. They also provide ways to inspect generated geometry, compare compiled
outputs, examine sharing and duplication, and estimate loading allocations.
The **Amiga runtime** determines the cost of using that data: visibility,
software rendering, lighting, loading, display conversion and gameplay.

The [AmiWind Map Optimization Toolkit](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md)
brings together the inspector, conversion work and validation tools. It is
still evolving. Individual optimization passes have their own implementation
and validation status. For example, the bounded hidden-surface detector has
produced zero house-interior cuts in documented trials; broader automatic
removal remains unfinished. See the
[measured findings](MAP_OPTIMIZATION_FINDINGS_2026-10-04.md) and
[hidden-surface status](EXTERIOR_HIDDEN_SURFACES.md).

The shared-sky work gives a concrete example of a completed reduction:
**301,751 local sky faces were removed across 2,664 exterior maps**. The
documented comparison, counting the shared sky resource once, saved
**131.324 MiB of disk storage**. That is a result for that conversion pass;
resident memory, loading time and frame time have their own measurements.
See the [build comparison](../README.md#v0028--trees-and-grass-day-and-night)
and [sky implementation notes](DAY_NIGHT_AND_SKY.md).

Making data smaller only counts as a useful optimization when the necessary
appearance and behaviour survive. Terrain joins, visible surfaces, texture
mapping, collision, shared placements and game state all matter. Even cutting
away a buried surface can create extra fragments, so the written result needs
to be checked and measured. The goal is a cheaper representation of the
experience we want to preserve.

## Is this complete Morrowind, here and now?

**No; not at the moment, but I am working on it.**

Getting all the assets in, implementing all the gameplay, and optimizing the
result are substantial parts of that work. The current scope is described below.

## How much of Morrowind is currently working?

As of **6 October 2026**, the public development snapshot is
**v0.0.29-dev4** and **v0.0.28** remains the latest stable release. "Stable"
here identifies the project's release track; AmiWind as a whole is still
an early work in progress. The September description of only a small town
area and a prison ship is out of date.

The documented playable scope now includes:

- Base-game Vvardenfell terrain and growing scenery, with more detailed Seyda
  Neen and Balmora areas and converted interiors.
- The opening registration and character-creation sequence, including race,
  appearance, class, birthsign and final review.
- Movement, mouse look, collision, doors, bounded NPC greetings and a character
  model gallery.
- A journal, world map and save support for the implemented character and
  progression state.
- Shared day and night skies, original-source stars and moons, torches, and
  converted music, voices, effects and video, with remaining event and audio
  checks tracked separately.
- A small mushroom-picking pilot in dev4: six original placements are packaged,
  with one pickup's disappearance and persistence accepted in the documented
  bounded native test.

World coverage and converted assets do not mean complete Morrowind gameplay.
Full combat, quest simulation, services, schedules, conversations and the
complete inventory system remain unfinished. Wider settlements, world actors
and interiors also need further work. The dev4 pickup state is a small piece
of interaction and persistence, and quickload still has an equipment-state
limitation. Tribunal and Bloodmoon world content are outside the current
playable scope.

See the [current overview](../README.md),
[dev4 release notes](RELEASE-v0.0.29-dev4.md),
[project state](PROJECT_STATE.md) and [roadmap](ROADMAP.md) for maintained scope
and outstanding work.

## Which tools help inspect the converted world?

The [polygon-count and heatmap inspector](https://github.com/FlyingFathead/amiwind/blob/main/tools/polycount_inspector.html)
was developed specifically for AmiWind. It helps examine the converted world's
geometry and the density of its scenes. Automated builds and tests support the
conversion pipeline; the source and applicable licenses are available in this
repository.


## What can future Amiga and m68k developers get out of this?

I want AmiWind to help make more ambitious projects possible on these machines.
Publishing the conversion tools, engine changes and findings gives other
developers material they can study, adapt and build on under the applicable
GPL terms.

That includes work on preparing demanding assets for constrained hardware,
organizing worlds into manageable pieces, examining geometry and memory costs,
and adapting a 3D runtime to the experience a developer wants to create. Some
parts are specific to Morrowind; others can inform entirely different games
and tools.

**Free and open source means the development can continue beyond this one
project.** Inspiring future Amiga and Motorola m68k development is part of the
purpose: **carry on the torch, and pass it to others.** The
[toolkit overview](AMIWIND_MAP_OPTIMIZATION_TOOLKIT.md),
[engine source](../engine/aga/Makefile) and
[licensing guide](LICENSING_AND_CREDITS.md) are starting points.

I want AmiWind to inspire aspiring Amiga developers to try ambitious
showcases of their own, and for more projects to follow. It is also artistic
self-expression: a way to remember Morrowind, keep creating on the Amiga,
and leave something for whoever wants to pick up the torch next.

## Do I need my own Morrowind files? What is included in the release?

**Yes. You supply your own Morrowind installation.** The tools convert its
data locally into content the Amiga runtime can use. Compiling the engine
alone does not require the game data. Emulator use additionally requires a
suitable licensed Kickstart ROM. Purchase Morrowind GOTY from
[GOG](https://www.gog.com/en/game/the_elder_scrolls_iii_morrowind_goty_edition) or
[Steam](https://store.steampowered.com/app/22320/The_Elder_Scrolls_III_Morrowind_Game_of_the_Year_Edition/).

The public source package includes source, tools, documentation and selected
demonstration media. It does not distribute the original or converted game
assets needed for play, a compiled AmiWind executable, Kickstart ROMs or
Workbench files. Playable images containing converted game assets are private
local build outputs. Start with the [build and setup instructions](../README.md#building-and-playing).

### Copyright and public distribution notice

**All AmiWind code is free and open source under the GNU General Public
License (GPL). No original game assets or ROMs are redistributed with
AmiWind's public source releases.**

The applicable GPL version depends on the component:

| Component | Licence |
| --- | --- |
| Selected Quake/AmiQuake AGA runtime | Distributed under GPLv2, preserving applicable original v2-or-later grants. |
| AmiWind's separate AGA additions and QuakeC | GPL-2.0-or-later. |
| AmiWind's host tools and original A500 runtime | GPL-3.0-only. |

Copyright remains with the respective contributors and rights holders.
Original and converted game assets, music, voices, ROMs and Workbench files
retain their own licensing; the code's GPL terms do not grant redistribution
rights to them. See [LICENSE](../LICENSE), the
[AGA runtime licence](../engine/aga/COPYING) and
[licensing and credits](LICENSING_AND_CREDITS.md).

## What would help establish what lower-spec Amigas can do?

Repeatable tests on clearly identified configurations will help turn the
optimization work into supported hardware targets. A useful report includes:

- The exact AmiWind version or commit, scene and player position.
- CPU or accelerator, clock/settings, Chip/Fast RAM and storage setup.
- Display backend, resolution and relevant rendering settings.
- Frame-time or FPS measurements, loading pauses and any visible or gameplay
  problems, preferably before and after the same change.

Comparing the same route or view makes it possible to tell whether an
optimization helped and what it cost elsewhere. Both measured successes and
well-described limits move the project forward. The
[memory notes](MEMORY_ALLOCATION.md), [cell-change checklist](CELL_CHANGING.md)
and [optimization roadmap](ROADMAP.md#assemble-first-then-optimize-the-measured-world)
describe the areas being investigated.

The ambition is to find ways of bringing the experience to lower-spec Amigas
once its assets are in and its content and costs are mapped out. The goal is
to reach **Morrowind, on the Amiga**, and leave the path open for others to
take it further.

---

Technical baseline for this FAQ:
[published dev4 source commit eb08c92](https://github.com/FlyingFathead/amiwind/commit/eb08c9249d788ffa05e9e8d0aa393417cdc009bd),
6 October 2026. RC1 is separately identified as in preparation; this FAQ does
not turn candidate checks into published-release or real-hardware acceptance.
The linked project documents provide more detailed and evolving status.

---

[Project overview](../README.md) · [Licensing and credits](LICENSING_AND_CREDITS.md) · [Roadmap](ROADMAP.md)
