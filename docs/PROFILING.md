# Profiling by runtime

For the AGA branch, see [OPTIMIZATION_HISTORY.md](OPTIMIZATION_HISTORY.md),
[checkpoint-006](CHECKPOINT_006_VALIDATION.md) and `tools/profile_aga.py`.
The following historical records describe the separate A500 reader.

# Native profiler and streaming experiments

The native runtime collects frame intervals, complete 16 KiB refill intervals,
track opens, reported audio starvation and I/O errors. Counters use CIA TOD ticks
(50 Hz in the tested PAL configuration). This measures emulated elapsed time,
not instruction-level CPU utilization or physical disk throughput.

## Matched refill experiment

FS-UAE 3.1.66, stock-speed cycle-exact 68000, OCS, PAL, 512 KiB Chip + 512 KiB
slow RAM, KS 1.3 revision 34.5. Each run uses the same stationary dense-fog scene,
complete title-track stream and 30-second native benchmark. These initial runs
used the same 64 MiB OFS layout; they isolate refill strategy, not image size.

| Strategy | Average fps | 95th percentile frame | Worst frame | Reported starvations/errors |
| --- | ---: | ---: | ---: | ---: |
| Blocking 16 KiB | 7.0573 | 320 ms | 360 ms | 0 / 0 |
| Async 16 KiB | 7.2618 | 300 ms | 320 ms | 0 / 0 |
| Async 8 KiB slices | 7.0670 | 220 ms | 220 ms | 0 / 0 |
| Async 4 KiB slices | 6.8288 | 160 ms | 160 ms | 0 / 0 |

The initial choice was **async4k** for smoother frame pacing. Its observed maximum frame
interval fell by 56% while average fps fell by about 3.2% against blocking reads.
One short run per strategy is evidence for this choice, not a confidence interval
or a guarantee for every view/controller. Rendering remains slow and unchanged.
Manual track changes are blocking and can take longer than these steady-state
frame intervals. Repeat matched runs after changing scene, storage or CPU target.

A complete refill's 95th-percentile elapsed time was 260/320/440/640 ms for
sync/async16/async8/async4 respectively. In async modes that includes drawing and
polling between slices. It must not be interpreted as the CPU cost of the disk
handler alone. The 48 KiB queue provides approximately 1.49 seconds after one
of its three blocks completes; observed latency headroom is not an underrun proof.

## Sustained-test correction

The initial per-frame async4k scheduler passed the fixed scene but reported 14
starvations during a longer moving/track-switching/fog-distance test. It could
not rely on one completed slice per rendered frame as frame times increased.
The runtime now also services audio at terrain depth and wireframe row boundaries
when at least four PAL ticks (80 ms) have elapsed since the last service call.
All renderer registers are preserved across that call. This is cooperative I/O
service, not a second rendering thread or a hard real-time guarantee.

The table above records the original controlled experiment. The corrected
scheduler's final fixed-scene and sustained results are recorded separately in
OPENING_VALIDATION.md; do not quote the original 160 ms figure as its final
worst-case frame interval.

## Reproduce

Build into an external new folder with `tools/build_opening.py`, supplying owned
assets and scene captures as described in OPENING_DEMO.md. Add
`--stream-mode async4k --benchmark-seconds 30`. Benchmark builds automatically
enter the fixed camera scene and exit; ordinary private releases use zero seconds
and remain interactive. Use identical inputs when comparing strategies.

```sh
python tools/profile_demo.py run --build /outside/benchmark-build --out /outside/new-run --rom /outside/kickstart.rom --emulator /path/to/fs-uae --emulator-version "FS-UAE 3.1.66, package 3.1.66-2build2" --xvfb /path/to/Xvfb --xdftool /path/to/xdftool
python tools/profile_demo.py compare /outside/run-sync/profile.json /outside/run-async/profile.json
python tools/profile_demo.py decode /outside/MWPROFILE.BIN
```

The runner supports `--emulator-data`, `--lib-dir` and `--xkb-dir` for extracted
Linux tools, and `--display` to select an unused X display. It needs Pillow for
a final screenshot. It clones the HDF before execution, verifies its source hash,
records ROM/emulator/executable hashes and the declared emulator version, and
checks the effective CPU/chipset/memory configuration. It mounts a small host
`PROFILE:` directory solely for benchmark results; music remains on the HDF.
The host harness is an X11 Linux workflow, not a WinUAE automation claim.

Interactive runs instead write `MWBOOT:MWPROFILE.BIN`. Wait at least ten seconds
at the DOS prompt before closing the emulator. Extract the result from a stopped
working image, for example with `xdftool image.hdf open part=DH0 + read
MWPROFILE.BIN /outside/MWPROFILE.BIN`. Do not alter canonical release images.

## Binary record

MWP1 is an 832-byte big-endian record. Header: magic, u16 version=1, u16 tick rate,
u32 strategy (0 sync, 1 async16, 2 async4, 3 async8), u32 benchmark duration ticks.
Twelve u32 values follow: solid frames/ticks, wire frames/ticks, reads, max read
ticks, total read ticks, starvations, errors, track opens, max solid ticks, max
wire ticks. Three 64-entry u32 histograms follow: refill, solid frame, wire frame.
Bin 63 also includes longer intervals; percentiles there are lower bounds.
Frame counters cover the runtime's capped measurement window (60,000 ticks per
mode); stream counts continue through exit. Benchmark comparisons verify clock,
duration, ROM, emulator executable, route, terrain and soundtrack metadata.

## Next optimization gates

- Add separate rendering, disk-handler and display-conversion measurements when
  investigating their individual costs; current frame intervals include I/O.
- Retest after introducing object streaming, higher fog distances or an A1200
  profile. Test control responsiveness while a request is outstanding.
- Compare an indexed filesystem archive to raw partition access before accepting
  the extra driver and bounds-checking complexity.
- Keep source ZIPs and private runnable checkpoints together, including the exact
  effective emulator settings and selected reports.
