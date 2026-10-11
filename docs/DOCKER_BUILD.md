# Docker builder

The tools/source-only builder wraps the established Linux pipeline. Native
Linux remains the reference; Windows Docker testing uses Docker Desktop's WSL 2
Linux engine. Docker sign-in is not required for this local builder.

<!-- contents start -->
## Contents

- [Build and validate](#build-and-validate)
- [Privacy and storage](#privacy-and-storage)
- [GitHub Actions and remaining work](#github-actions-and-remaining-work)
- [Full private build (game-entry checkpoint passed)](#full-private-build-game-entry-checkpoint-passed)
- [Watch a build in the Monitor](#watch-a-build-in-the-monitor)

<!-- contents end -->

Install Docker separately and start its Linux engine before using this helper.
Do not enable Windows login autostart unless you want it. Shut Docker down after
use if you want its CPU/RAM released; images and named volumes remain retained.

## Build and validate

From the source checkout, use Python 3.10+ and Docker:

```sh
python tools/build_docker.py check --context ../docker-context-001 --output ../docker-results-001
```

Paths are relative to your current directory. Context and results must be new,
separate directories outside the source tree (ignored `out/` is also permitted).
No existing context, evidence or volume is deleted. Pick new directories on a
retry. The default named volume `amiwind-docker-builds` retains Linux build files;
`--volume` selects another volume. `--jobs` defaults to the host CPU count and
reaches the build unchanged; see [Parallel host builds](PARALLEL_BUILD.md).

On Windows PowerShell, `python` can be the full path to your installed Python.
Quoted context/results paths may contain spaces. Docker must be available on
PATH, or pass `--docker` with its executable path. `--docker-host` optionally
selects an explicit engine endpoint without changing global Docker settings.

`context` validates the public source and prepares only the build context.
`build` additionally creates the local image. `check` builds it, runs source
checks, confirms the image tools (NIF reader), runs a short set of builder test
modules in the image, then compiles an asset-free Amiga test image. This
boot-notice image is not a playable game and uses no game data/ROM. Add
`--full-suite` to run the full synthetic regression suite in the image instead
of the short set; hosted CI runs the full suite once, in its source checks job.

The Ubuntu base is pinned by digest; SDK/map-tool downloads and reference qcc
use the existing verified Linux bootstrap. Ubuntu package and unpinned Python
package updates remain possible: logs and build receipts record selected versions.
This is a validated recipe, not a claim of byte-for-byte reproducible dependency
resolution. See [dependency references](BUILD_DEPENDENCIES.md).

## Privacy and storage

The helper copies only source accepted by `tools/release.py`, never the checkout's
parent directory or ignored private files. A restrictive `.dockerignore` adds a
second boundary. No Morrowind files, converted assets, ROMs or playable HDFs are
accepted as image-build inputs. Do not add them to the context manually.

Heavy output lives in the Linux-backed named volume rather than a Windows bind
mount. Results contain the full image-build/validation logs and a status/source
checksum receipt, including failed commands. Build-stage receipts and the test
image remain in the volume under `/work/build/<run>/`; the run is recorded in
`docker-result.json`. Do not delete that volume if you need those outputs.

Allow roughly 30-40 GiB initially for image/cache and future private conversion
work, then measure actual consumption. This is headroom, not a preallocated disk
or a fixed full-game requirement. The first prototype image was about 2.56 GiB;
full-game Docker peak storage has not yet been measured.

## GitHub Actions and remaining work

The `docker-builder` job builds the same allowlisted context, bootstraps tools,
runs synthetic regressions and performs an asset-free Amiga compile. Diagnostic
logs/receipts upload on success or failure. Existing native Linux and Windows
checks remain separate. The hosted Docker job runs for every published release (most recently
[v0.0.35](RELEASE-v0.0.35.md)). Each source release requires its own exact-commit CI; local prototype
success does not establish hosted CI success.

The owner-input/export helper completed the full v0.0.26 conversion and exported
the verified final-identity HDF. The strict actor-ground gate passed with zero
unresolved findings; WinUAE game entry, opening movie and Enter/Escape controls
passed. Those are dated full-game results. Published v0.0.27 subsequently
passed all four hosted jobs, its full Linux Docker suite and asset-free compile,
with release/download verification complete; these do not establish another
full-game Docker conversion or target playthrough. See the
[v0.0.26 record](RELEASE-v0.0.26.md), [v0.0.27 release](RELEASE-v0.0.27.md) and
[Docker roadmap](DOCKER_BUILD_ROADMAP.md).

## Full private build (game-entry checkpoint passed)

After building the tools-only image, pass your owned installation to the runtime
helper. This never supplies game data to `docker build`:

```sh
python tools/run_docker.py --data-files "/path/to/Morrowind/Data Files" --output ../docker-full-results-001
```

On Windows, input staging is enabled by default. The helper streams a private
copy into a new Linux-backed named volume and mounts it read-only during the
conversion. This storage is provided by Docker's virtual disk on the Windows
host; it does not require a separate Linux partition. On Linux, the default is
a read-only bind mount; `--stage-inputs` selects the same volume-copy method.
`--no-stage-inputs` avoids copying, but Windows file access can be much slower.
Original files are never changed. Copies remain private runtime storage and
never become image layers. Retain enough host disk space for the copy.

A staged copy can be reused through `--input-volume <name>` instead of
`--data-files`; the helper refuses a missing or already-existing staging volume.
The converter rechecks inputs on every full run. Never mount the input volume
as the writable output volume. Conversion always runs with `--network none`.

Full output and cache use `amiwind-docker-builds` by default; `--volume` changes
it. Each run is a folder `/work/build/<run>/` in that volume, named
`YYYY_MM_DD_vVERSION_full-docker_<commit>` unless you pass `--name`. The helper exports a
successful run to the requested new results directory.
Failures retain logs, receipts, volume and container for diagnosis. A completed
HDF still requires host-side emulator testing using your own Kickstart ROM.
## Watch a build in the Monitor

The AmiWind Toolkit's **Monitor** tab follows a Docker build while it runs: the live log of the running
stage, every stage against its expected time, the ETA and the cores in use
([Monitor](AMIWIND_TOOLKIT.md#monitor)). It needs nothing installed: Python's standard library and Docker.

1. Build, as above (one command):

   ```sh
   python tools/run_docker.py --data-files "/path/to/Morrowind/Data Files" --output ../docker-full-results-001
   ```

2. In a second terminal, from the source checkout, start the Monitor on the same volume (one command):

   ```sh
   python tools/toolkit_serve.py --monitor-docker amiwind-docker-builds --open
   ```

   `--monitor-docker VOLUME[:PATH]` reads the run folders under `PATH` in the volume (default `build`, where
   the helpers write them) through a throwaway container of the image the helper built
   (`amiwind-builder:local`; `--monitor-image` picks another image that has `python3`). Without `--open`,
   open the address it prints (`http://127.0.0.1:8031/amiwind-toolkit/monitor.html`).

What it guarantees: the container is started with the volume and the reader mounted read-only, a read-only
root, no network, no capabilities, an unprivileged user and half a core, and it is removed when the server
stops. The page and the server only read: the `/monitor/` endpoints answer GET only, every run and log name is
checked and must lie inside the builds folder, and logs are read in capped byte ranges. Nothing a page sends can
change the container's command.

**From a phone.** The server listens on this machine only (127.0.0.1) by default, so a phone cannot reach it.
To watch from a phone on your own network, start it with `--bind` and this machine's LAN address, for example
`--bind 192.168.1.20`, and open `http://192.168.1.20:8031/amiwind-toolkit/monitor.html` on the phone. Do this
only on a network you trust: everyone who can reach that address can read what the server serves (the Toolkit,
your data and your build logs). It prints a warning when it does, and refuses an every-interface address: it always listens on the one address you name.

### Historical cold rc1-identity build

The cold private full conversion on Windows 11 / WSL 2 completed on 2 October
2026 using 24 workers and no network. All 3,551 NPC models and 2,526 terrain
regions passed; packaged actor-ground validation found zero unresolved issues.
It took 35 minutes 3 seconds, excluding provisioning and emulator testing, and
produced a 3,489,693,696-byte rc1-identity HDF. WinUAE game entry and keyboard/menu
controls passed. See [cold-build evidence](VALIDATION-DOCKER-2026-10-02.md).

### Final v0.0.26 helper/export build

The final helper/export run completed the same full content and strict actor-ground
gates with zero unresolved findings. Its verified v0.0.26 HDF is 3,489,693,696
bytes, SHA-256 `da3f80b3d7ebefe30c53031fdd29c34a094d0b486328daa46739a4a5ad6364a3`.
Conversion elapsed was 1,566.061 seconds (26 minutes 6 seconds), excluding export, provisioning and emulator testing; the cached run reported 78 warnings. WinUAE 6.0.3
played the opening movie, entered Jiub's prison scene and responded to Enter/Escape.
Hosted Docker CI subsequently passed for v0.0.26 and v0.0.27. Synthetic CI
remains separate from this owner-supplied full-game validation; every future
publication still requires its own exact-commit hosted result.
