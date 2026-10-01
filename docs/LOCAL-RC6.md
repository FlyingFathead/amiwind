# Local source checkpoint: v0.0.25-rc6

Use the single complete-update bundle and its handoff instructions. It applies
directly to the rc3 checkout with backup and conflict detection. Earlier rc4/rc5
updates and separate roadmap patches are included and need not be applied.

The reported rc3 build completed terrain but failed its image-stage UI receipt
check. Keep that run: use [image recovery](IMAGE_RECOVERY.md) after updating.
This checkpoint fixes the receipt and adds recovery; it does not implement the
planned persistent world cache, profiler, GPU backend or native Windows setup.

New builds receive the [completion footer](BUILD_OUTPUT.md). The Windows host
helpers and explicit make interpreter propagation are included. The
[toolkit roadmap](BUILD_TOOLKIT_ROADMAP.md) prioritizes reducing terrain build
time before further host portability or speculative compiler work.

Use a fresh run name and keep tools/output outside the source tree:

```bash
(
set -euo pipefail
cd /path/to/amiwind
bash build.sh --autoinstall \
  --data-files "/path/to/Morrowind/Data Files" \
  --tools-dir "/path/to/amiwind-tools" \
  --workspace "/path/to/amiwind-tests" \
  --name "rc6-local-$(date +%Y%m%d-%H%M%S)"
)
```

See [rc6 release notes](RELEASE-v0.0.25-rc6.md) and the
[source validation receipt](validation/rc6-source.json). Full game conversion,
production image gates and emulator testing require their own evidence. The
owner publishes the source prerelease with the provided script after review.


If rc3 conversion already completed, use [image recovery](IMAGE_RECOVERY.md)
instead of the full-build command above. The strict actor gate still fails on
the known 23 findings. An explicit reviewed-report option is available only for
private diagnostic acceptance. A completed rc3 private HDF does not need to be
rebuilt merely to install the source/documentation update. It retains its rc3
version. Rebuild the engine/image only when an rc6 diagnostic HDF is needed.
