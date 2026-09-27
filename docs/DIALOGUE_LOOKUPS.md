# Ordered voice-record lookup export

`tools/prepare_dialogue_lookup.py` reads the owner's base Morrowind master and
writes a private JSON index. The guided AGA build runs it as `dialogue-lookup`;
its output is beside the build stages, not embedded in the HDF yet.

```sh
python3 tools/prepare_dialogue_lookup.py --data-files '/owned/Morrowind/Data Files' --out ../private/voice-lookup.json
```

Preserved categories: Hello, Idle, Intruder, Thief, Hit, Attack, Flee and Alarm.
Each response retains record order, IDs and links, raw subrecords, static actor
filters, ordered conditions and operands, text/sound path and result script.
The actor index initially covers Fargoth and the imperial-guard base record.
The tested installation exports 4,614 responses; this is not an actor count.

Static candidates are not an eligible playback pool. Runtime globals, local
variables, disposition/ranks, random conditions, quest state and supported
scripts still need an evaluator. Do not shuffle all files in a voice directory
or silently treat unsupported conditions as true. This base-master tool does
not implement mod merging or the complete dialogue engine. Native actors still
use one preselected Hello per appearance, with existing distance/reset/cooldown.

The public tests generate fictional records. The exported table contains owned
game data and belongs only in the private workspace/checkpoints.

References:

- [OpenMW ordered filtering](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwdialogue/filter.cpp)
- [OpenMW dialogue manager](https://github.com/OpenMW/openmw/blob/46bd4599203ee52ffc0f3e8edb3fc159a0303a49/apps/openmw/mwdialogue/dialoguemanagerimp.cpp)
- [UESP generic voiced dialogue](https://en.uesp.net/wiki/Morrowind:Generic_Dialogue_Voiced)

UESP is a useful development reference for lines and filenames. The owner's
ESM records and their conditions determine selection; the wiki is not a runtime
asset source. See OPENMW_REF_NPCS_AND_DIALOGUE.md for trigger behavior and scope.
