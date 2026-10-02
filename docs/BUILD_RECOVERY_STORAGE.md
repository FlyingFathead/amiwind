# Build storage and recoverable checkpoints

Check available storage and memory **before** an expensive build. Include game
inputs, tools, conversion output, persistent caches, staging, temporary/final
images and verification copies. Shared-memory scratch consumes RAM as well as
its filesystem capacity. A writable directory or a large host disk does not
establish the process's available quota. Never omit either gallery or required
assets to fit the budget; arrange capacity first.

A transient working directory is not a durable checkpoint. Preserve completed
work outside that environment and verify the saved archive before treating it
as recoverable. The current builder does not automatically upload backups.

Keep these recovery inputs distinct:

- Complete public source kit, SHA-256 and source version, including the supported
  apply/build/recovery/publication instructions. Published Git history alone does
  not preserve an unpublished source edit.
- Private original game inputs, or a reproducible installation plus its input
  checksums. Do not put original or converted game assets in public Git/releases.
- Toolchain identities, versions and source/build provenance needed to reproduce
  conversion. Keep obtainable SDKs separately from irreplaceable work.
- Retained build directory with `build-state.json`, logs, completed terrain/music
  and model/receipt pairs. The original rc3 terrain run and a stopped rc9 gallery
  run are different recovery inputs; neither should be overwritten.
- Verified persistent NPC cache with its model bytes and identity receipts.
  Back it up between runs when conversion cost justifies it. Stop writers before
  taking a filesystem-level snapshot, or validate each saved pair on restore.
  rc10 rejects incomplete/corrupt pairs and reconverts them; this is integrity
  protection, not a substitute for a durable copy.

A checkpoint must record what was completed, what failed, what remains untested,
archive byte sizes and SHA-256, and where the necessary inputs/tools can be
recovered. Test archive integrity and check restored manifests/hashes. Never
label a partially tested source checkpoint as a successful full-game build.
Retain the previous verified checkpoint until the replacement has been saved and
checked. Do not delete the only completed conversion to make room for packaging.

For repeated builds use [persistent NPC reuse](NPC_MODEL_CACHE.md) and
[image recovery](IMAGE_RECOVERY.md). A warm cache avoids rebaking unchanged
appearances; it does not yet provide component-level conversion reuse, runtime
mutable equipment or incremental world-terrain generation.
