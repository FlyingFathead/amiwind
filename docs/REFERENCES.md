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
