# Complete media import and coverage

Normal AGA builds run a complete media stage alongside scene preparation. It
imports available sound files, including voice recordings not referenced by the
installed masters, converts the installed soundtrack, and converts all installed
BIK videos. Optional absent source files produce warnings. A failed conversion
or missing staged file is counted separately from missing original input.

The converter reads the available Morrowind, Tribunal and Bloodmoon masters and
archives, then applies loose-file overrides. It records source dialogue and sound
lookups with the original identifiers and converted paths. These are lookup
records, not an implementation of every dialogue condition or sound trigger.
The private catalogue also retains ordered INFO/SOUN subrecords byte-for-byte
(hex encoded), source record flags and positions in the fixed master order;
deleted records are separate tombstones and never count as playable references. A deleted DIAL is retained as a topic tombstone and still supplies the literal topic context for following INFO source records.
This preserves conditions and provenance for later auditing without evaluating
conditions or load-order overrides. Text-only dialogue remains text-only.
Non-audio metadata files are listed as ignored, rather than counted as recordings.

Sound outputs use mono 11,025 Hz unsigned 8-bit PCM WAV. Filenames are short,
stable hashes of canonical source paths; collisions are rejected before import.
The existing soundtrack stage retains its streaming music format. Videos use
AWV1, with the existing higher-resolution story intro preserved when its original
source digest matches. Silent source videos receive a matching silent PCM track;
an actual audio decoding failure remains an error in the coverage report.

Each run saves `media/source-inventory.json` and `media/media-coverage.json`.
Assembly checks output hashes, original soundtrack identities and copied files,
then writes `image/media-coverage.json`. The game payload contains the lookup
catalogue at `id1/media/catalogue.json` and the numeric video list at
`id1/intro/videos.awl`. Extra installed videos retain path lookups without changing
the stable numeric IDs of the known videos.

The final build summary shows included, available, missing-source and
missing-output counts separately for videos, music, voices and effects. Coverage
from a failed build is labelled as conversion or staged-payload coverage. Only a
completed image with successful payload readback can claim final image coverage.
The summary reports all 17 known GOTY videos included only when that exact set of
counts is complete; missing expansion files never count as included.

Importing the library does not preload it into Amiga memory, and does not imply
that every event is wired to playback. Runtime selection, caching, streaming and
event acceptance are separate checks. All original and converted game media,
catalogues containing dialogue, and build receipts belong in private build
directories. They must not enter the source repository or public source ZIPs.
