# Format and hardware references

The initial tools are standalone Python. They use the file layouts described by
OpenMW's sources; they do not bundle or link an OpenMW engine or Hunter binary.
OpenMW was inspected at commit `46bd4599203ee52ffc0f3e8edb3fc159a0303a49`.

- [TES3 BSA layout](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/bsa/bsafile.cpp)
- [LAND height and material decoding](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/esm3/loadland.cpp)
- [Terrain dimensions and layer indexing](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/esm3/landrecorddata.hpp)
- [Cell references](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/components/esm3/cellref.cpp)
- [OpenMW game-file installation](https://openmw.readthedocs.io/en/stable/manuals/installation/install-game-files.html)
- [Amiga audio hardware](https://www.theflatnet.de/pub/cbm/amiga/AmigaDevDocs/hard_5.html)
- [Hunter performance patch](https://github.com/timoheimonen/amiga-hunter-performance-68060)

OpenMW code reuse in a later converter must retain its applicable licensing and
notices. These format experiments do not establish a public project's final
license or its game compatibility.

## Morrowind dialogue reference

[UESP: Generic Dialogue Voiced](https://en.uesp.net/wiki/Morrowind:Generic_Dialogue_Voiced)
is a useful community index for voiced lines and their associated audio filenames.
Use it when matching greetings and other voice cues to files in an owner's
installation, alongside the installed master records. It is a reference, not a
replacement for original game data or a grant to redistribute the recordings.
The converter must continue to read the owner's local files.

For the first Fargoth/guard milestone, see [NPC and greeting behaviour](OPENMW_REF_NPCS_AND_DIALOGUE.md), including the requested UESP voice reference and OpenMW selection/trigger paths.

## Game mechanics research

Use UESP as a community research guide alongside the owned master/scripts,
controlled original-game observations and OpenMW source. Preserve numeric
conditions, exceptions and competing evidence instead of inferring a general
rule from one opening event. Record access failures and use supplied excerpts
without pretending they were fetched live.

- [UESP: Attributes](https://en.uesp.net/wiki/Morrowind:Attributes) — character
  fields and later attribute-effect research. Owner supplied the page text on
  28 September 2026; the page reports a 24 October 2025 revision. Direct access
  returned HTTP 403 in this session. Retain the eight primary fields, distinguish
  base/modifier/current values and derived resources; defer full gameplay effect
  calculations until fundamental state, interaction and persistence work is ready.
- [UESP: Console](https://en.uesp.net/wiki/Morrowind:Console) — command and
  inspection reference requested for production. Direct access also returned
  HTTP 403 in this session. Use original scripts/records for actual dialogue
  substitutions and command semantics, and verify engine behavior in OpenMW.
- [OpenMW placed-object rotation](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/components/misc/convert.hpp)
  and [scene attachment](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwworld/scene.cpp)
  — direct object transforms used in the invisible-barrier investigation.
- [Opening state conditions](CHARACTER_CREATION.md#persistent-rule-opening-access-is-conditional-world-state)
  and [trial/fix journal](IMPLEMENTATION_JOURNAL.md) — local findings and their
  validation status. A passing local check is separate from owner acceptance.

- [UESP: Classes](https://en.uesp.net/wiki/Morrowind:Classes) — owner supplied
  page text on 28 September 2026, identifying a 9 August 2026 revision and
  CC BY-SA 2.5 attribution. Reference only; do not reconstruct the flattened
  comparison table as authoritative data. Read exact playable class records
  from the owned master. See the class checklist in CHARACTER_CREATION.md.
- [OpenMW GetDistance](https://github.com/OpenMW/openmw/blob/openmw-0.49.0/apps/openmw/mwscript/transformationextensions.cpp)
  — full Euclidean distance between reference positions; compare matching actor
  anchors after converting to native coordinates.
