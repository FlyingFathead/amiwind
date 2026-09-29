# v0.0.21-dev6 paper-font checkpoint 002

Date: 29 September 2026. Status: source working checkpoint, not a completed
release, parallel-build delivery, or validated new private playable.

## Scope

Implement the owner's approved paper-only bitmap candidate and an opt-out.
TTF stays preferred. The candidate defaults on only for the actual bitmap reading
path; TTF and ordinary dialogue/menu output remain unchanged.
See [settings and implementation](PAPER_FONT_OPTIONS.md).

The filled candidate matches the approved preview title and four body lines
pixel-for-pixel in the host comparison. Its AWF SHA-256 is
`b865470fc8f31cd15ceb960c953b8d6a49210cdf8a1bbdb128ed9a6b184bf339`.
Original and candidate are each 4,535 bytes with identical 256-glyph metrics.
The exact supplied font inputs were tested privately, not bundled in source.

## Validation

- Focused Python/font/native tests: 20 passed. The native isolation test exercises
  seven separate cases against compiled C with undefined-behavior checks.
- Broader suite: 234 tests, 230 passed, two skipped and two errors. Both errors
  were reproduced on the unchanged supplied dev5 snapshot: the host lacks
  `fast_simplification`, and the CPU-job test's mocked OSError escapes through
  Python 3.13's `os.process_cpu_count()`. Neither was fixed or hidden by this
  font checkpoint. This is not a fully green suite on this host.
- Supplied-font diagnostic: original versus candidate hashes verified; all twelve
  ordinary bitmap family/size outputs match dev5; TTF paper bytes are unchanged
  with either ink setting.
- No new Amiga compilation, HDF, emulator session or physical-hardware run is
  claimed. The owner's earlier successful Steam HDF build was dev5.

## Baseline and use

Exact base: owner snapshot `amiwind-2026-09-29_003353.zip`.
Base archive SHA-256: `2a3eb8322ac871a5616d3a4dd3ca56e1ed5b1c7ef1b418ca8cb1e191ef029267`.
The owner identified this as the published dev5 tree at commit
`cd339b89a1bc7d59c6b0c8be2ad81033baa4610e`; no live Git operation was performed here.
The patch is against this source snapshot, not an unprovided in-progress tree.

Use a separate working directory for this checkpoint. Existing dev5 archives and
private HDFs are preserved. Do not replace or retag the dev5 release. No source
files are removed by this checkpoint. Prior release presets remain available.

## Remaining dev6 work

The requested whole-pipeline parallel scheduler, bounded per-asset worker pools,
shared CPU budget and legacy serial escape hatch remain pending in this snapshot.
Do not infer parallelization from this version number. No build-time speedup is
claimed. Complete that work and matched validation before publishing dev6 as the
parallel-build release.

Paper-only native/emulator visual acceptance also remains pending. Existing
world-mapping, gameplay and stability issues remain as recorded in the baseline.
