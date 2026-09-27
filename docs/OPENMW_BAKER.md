# OpenMW as the host-side character baker

The intended rendering backend is OpenMW itself: use its original-data loading,
equipped actor assembly, animation evaluation and renderer on the PC. The Amiga
receives converted assets and runs a separate native runtime. The actor backend is
not implemented or bundled. Current still-image capture runs a separately
installed OpenMW process; it does not embed engine code in the converter.

## Intended responsibilities

| Component | Responsibility |
| --- | --- |
| Our job planner | Select appearance recipes, animations, times, directions and sizes |
| OpenMW host backend | Load actor/body parts, equip items, evaluate pose and render |
| Our image processor | Crop with stable anchors, quantize palette, create masks/bitplanes |
| Our asset packer | Deduplicate, index and group frames for bounded target reads |
| Native Amiga runtime | Select frames, draw, run game logic and schedule streaming |

Clothing and weapons are attached to the posed 3D actor before rendering. This
lets the renderer resolve visibility and occlusion in each captured view. Shared
body/rig templates and combat-style clip sets reduce repeated setup work; they
do not make different outfits share identical bitmap pixels.

## Integration approach to test

Start with a controlled OpenMW scene containing one actor. Apply a known equipped
appearance, select an animation and verify sampling from eight directions.
The documented Actor equipment and animation APIs provide useful controls, with
local/self restrictions that a test actor script must respect.

For reliable batch capture, add the smallest necessary engine hooks for a fixed
simulation time step, deterministic pose evaluation, isolated camera/background,
image/mask capture and completion reporting. An OpenMW-based batch mode or small
companion application may be necessary. OpenMW is not assumed to expose every
engine subsystem as a simple standalone library, and no ready-made offline
sprite-export command has been established.

Pin the engine revision and capture settings in the cache key. Keep installation
files, engine checkout/builds and generated frames in the external workspace.
The existing Python ESM/BSA auditor remains useful for terrain and inventory;
it is not a replacement implementation of the character renderer.

## Modification and distribution

OpenMW identifies its source licence as GNU GPL version 3. Modification is
permitted under that licence. A distributed modified OpenMW backend must retain
the applicable licence/notices and satisfy the corresponding-source obligations.
Original Morrowind assets remain user supplied; the engine licence does not
provide them. Review actual dependency licences when building/distributing the
backend. No modified OpenMW binary or source is shipped in this initial package.

Sources: [OpenMW FAQ and licence statement](https://openmw.org/faq/),
[OpenMW source licence](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/LICENSE),
[GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html),
[equipment API](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_types.html),
[animation API](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_animation.html).

## Available implementation option

A pinned, redistributed OpenMW-derived host baker is an accepted project option
if the external-process capture interface proves insufficient. Keep the exact
upstream revision, local changes, file provenance, applicable licence/notices,
build instructions and corresponding source with that component. Review bundled
dependencies separately. Limit imported code to the concrete baking requirement;
no engine code is imported merely to advertise OpenMW involvement.

The project source now uses GPL-3.0-only. That does not replace upstream file
notices or remove obligations for a distributed modified OpenMW build. Game data
and generated sprites/audio remain outside the public packages. A user supplies
Morrowind locally, the host baker converts it, and the native Amiga runtime reads
the converted result. None of the current packages bundles OpenMW source/binaries.
