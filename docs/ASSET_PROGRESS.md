# Asset progress and provenance

See the dated [asset coverage report](ASSET_COVERAGE.md) for current counts,
known omissions and runtime coverage limits.

Use `tools/asset_progress.py` to compare an original-data inventory, a media
conversion report and a verified image readback. Run it inside the development
container; keep the original data and generated reports outside this repository.

```sh
python3 tools/asset_progress.py \
  --data-files /input/DataFiles \
  --media-report /work/media/media-coverage.json \
  --image-readback /work/image/readback.json \
  --out /work/reports/asset-progress-001
```

The output directory must be new. The command writes `progress.json` and
`progress.md`. Input reports are identified by SHA-256. The inventory considers
the three standard TES3 archives in base/expansion order, then loose-file
overrides, with case-insensitive paths. Root archive and master containers are
excluded from asset totals. This is the supplied data set, not a universal
definition of every possible installation or plugin load order.

The media input uses the `entries` and `categories` fields emitted by
`prepare_media_assets.py`. Image readback is a list of partition records, each
with `readback: "passed"` and a `files` list containing `path`, `bytes` and
`sha256`. Duplicate image paths with conflicting records and media categories
that disagree with the canonical source path are rejected.

## Read the columns correctly

- **Source paths** counts unique normalized file paths, not world placements,
  NPC records, quests or unique visual models.
- **Recorded converted** counts successful source paths in the supplied media
  conversion report. These are recorded batch results, not a fresh conversion
  or proof that today's selected source bytes are unchanged. Zero means no
  successful rows in that supplied batch. Geometry and other categories remain
  unknown without their own complete conversion provenance.
- **Current input verified** stays unknown. The inventory scans names and
  lengths without rehashing all selected archive entries and loose overrides.
  A `source_sha256` in an earlier conversion receipt cannot itself verify the
  current input. JSON makes this explicit with
  `current_input_verification: "not_checked"`; it does not classify the old
  conversion as stale or invalid. Rebuild/revalidate the affected converter
  when a source changes, and preserve its input digest chain.
- **Same output in image** requires matching output path, byte length and hash.
  Zero can mean the image contains an older or different conversion. It does
  not imply the image has no audio or videos.
- **Missing references** counts requested paths absent in the supplied batch.
  **Failed outputs** comes from the media report's separate missing-output
  count. Keep those causes separate.
- **Runtime accepted** stays unknown. Conversion and image readback alone do
  not prove that a game event finds an asset, that it looks or sounds correct,
  or that its performance is acceptable.

The report also counts packaged artifacts by extension. A converted asset may
produce several files, while several source files can contribute to one atlas.
Do not divide artifact counts by source-path counts to claim import completion.

For other conversion stages, maintain separate rows with a common unit and
scope: source identity, total, converted count, packaged count, runtime accepted
count, evidence and an explicit reason for unknown values. Keep postprocessing
hash chains when palettes or formats change after initial conversion. Track
settlements, interiors and quest behavior separately from file coverage.

Private reports can contain game-derived inventory information. Do not include
them, original assets, emulator ROMs or recovery images in public source bundles.
