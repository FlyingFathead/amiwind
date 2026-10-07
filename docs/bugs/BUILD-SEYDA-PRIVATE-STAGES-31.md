# BUILD-SEYDA-PRIVATE-STAGES-31: repository builder cannot regenerate the shipped Seyda Neen maps

## Status: 8 October 2026

Closed: duplicate of [BUILD-SEYDA-REGEN-30](../BUG_JOURNAL.md#build-seyda-regen-30-public-build-cannot-regenerate-seyda-neen-7-october-2026),
recorded again while preparing v0.0.31. Current status lives there. Note: the image
build has had `--canonical-land-source` since v0.0.30-dev5; the remaining gap is
the three private stages below.

## Symptom

A full image build from this repository does not reproduce the Seyda Neen
sub-cell maps that the playtest and release images contain, and as written it
stops before Seyda: terrain culling is enabled by default, but the image
build passes no canonical terrain source to the Seyda region conversion.

## Where

`tools/build_aga.py image` (Seyda region conversion call), the Seyda region
tools, and the later stages that produced the shipped maps.

## How it happened

The shipped Seyda maps are the end of a seven-stage chain: the full-town mesh
map and its partition (public tools), the image finalisation passes (public),
then a canonical terrain fit, a palette remap and a ground-winding repair that
were run as one-off scripts outside the repository. Later releases cloned
earlier images and patched individual files instead of rebuilding maps, so the
public path was never exercised end to end.

## Why it was not caught

Release checks verified the published source archive and the playtest image
separately; nothing required the repository builder to reproduce the image.

## Reproduction

Run `tools/build_aga.py image` from this repository with Seyda culling enabled
(the default) and no canonical terrain source.

## Repair

Bring the three missing stages into the repository as tested builder steps,
pass the canonical terrain source in the image build, and add the release gate
in [RELEASE_WORKFLOW.md](../RELEASE_WORKFLOW.md): a clean repository build must
reproduce the release payload.

## Verification

Pending: a full repository image build compared file by file with the release
image.

## Prevention

The release gate above.
