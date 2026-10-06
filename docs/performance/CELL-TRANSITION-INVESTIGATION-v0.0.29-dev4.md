# Cell-transition pauses and read-ahead investigation (v0.0.29-dev4)

**Status: open.** The measured route still spends roughly 1.1 seconds in the transition-ready/presentation timing path. A bounded source candidate corrects one prediction error. A fresh native comparison improves prefix reuse but has mixed timing results; actual first-world-frame acceptance remains unmeasured. No overall speedup is claimed.

## What was measured

Eight automatic outdoor crossings were recorded on one fixed route: four with each of two loading methods, split across both travel directions. The route used a fixed-height noclip movement to isolate loading; it does not represent ordinary walking, collision, or all boundary shapes. Assets and the engine were held constant within the run.

The recorded ready/presentation-callback estimate ranged from **1.070 to 1.149 seconds**. Directional medians were about **1.104 s southbound and 1.140 s northbound** for method 1, and **1.075 s and 1.110 s** for method 2. That is roughly a 30 ms median difference in this small warm-route sample, not evidence of a repeatable improvement. Method 2 filled its bounded 128 KiB prefix on all four crossings, but only one later load reused any bytes (130,948). Three prefixes were not consumed: both southbound misses match the replayed early target switch, while the remaining northbound miss is unexplained.

Instrumented model-file reads accounted for roughly **78.9–79.7% of server loading time**, while measured decode was about **4.8–5.2%**. The timed read is guest elapsed time inside the model loader, not a measurement of physical-device throughput. It excludes some file operations outside that loader, such as other open/seek/read paths. These figures point toward investigating synchronous file and cache behavior first; they do not establish a physical storage bottleneck.

## Prediction finding and current source candidate

A replay of the region-selection logic showed a concrete failure mode: endpoint look-ahead can advance to a farther region before the immediately crossed region becomes resident under the crossing hysteresis. The stream then cancels the still-useful prefix as the path target changes. In the replay, this happened about half a second before the nearer region was admitted. This is consistent with the two southbound crossings that filled and reused no prefix; native per-frame prediction/cancellation events were not recorded. A northbound filled-but-unconsumed prefix also remains unexplained.

The current unsealed source candidate changes method 2 to predict the first crossed region rather than skipping ahead to the endpoint. Method 1, the default, and the stream reader are unchanged. Four focused source-level C fixtures pass; a 68040/FPU object compile passes, and the v0.0.29-dev4 integration run has 916 tests: 912 passed and 4 skipped, with no failures or errors. A replay control fails under the old endpoint prediction and passes under the candidate. These checks establish the source/compile result; the separate prediction-only native follow-up is below.

## Matched native follow-up: prediction improves, timing remains mixed

A separate fresh comparison used method 2 for both the unchanged control and
the prediction-only candidate: four counted crossings each, two per direction,
with two warm-up crossings per engine. The capacity remained 128 KiB and the
look-ahead remained 1.5 seconds. These eight samples are separate from the
earlier method-1/method-2 baseline above.

The candidate consumed a prefix on **3 of 4 crossings**, versus **0 of 4** for
the fresh control. Both southbound candidate attempts retained a filled
131,072-byte prefix; one consumed 130,945 bytes and one consumed none. The
filled-but-unused case still needs diagnosis.

Ready/presentation-callback medians were **1,100.757 to 1,119.780 ms** southbound
and **1,154.541 to 1,093.892 ms** northbound. Thus one direction became about
19 ms slower and the other about 61 ms faster. With only two samples per
direction and differing read/cache workloads, this does **not** establish an
overall speedup or smoother transitions. State readbacks passed in this route;
audio counters alone do not establish uninterrupted voice/music waveforms.

Further source-review leads are prefix cache lifetime during hunk allocation,
redundant file opening/seeking, and real world-draw/display-generation markers.
These are investigation leads, not implemented optimizations or established
causes of the remaining miss. In particular, a filled buffer may have become
nonresident before the copy hook; that must be measured before changing its
allocation policy or size.

## Timing caveats

The existing load profile records file-read, decode, world, actor, server-total, and prefix counters. These phases overlap: world and actor work includes reads and decode, so their durations must not be summed as if independent CPU phases. Read bytes and cache workloads also varied between samples.

The current “visible” timestamp is a ready/presentation-callback estimate, not proof that the destination world was actually drawn. Its callback runs after the screen-update routine returns, and that routine can return early without drawing the new world. Some heap auditing also occurs before the timestamp. Keep the raw measurements for comparison, but label them accurately until a real draw-and-display marker exists.

The existing profiles do not identify prediction cancellation reasons, per-transition file-open/seek versus read costs, model/cache-hit attribution, or transition-scoped voice/music continuity. Whole-session audio counters cannot prove that an active voice or music sample cursor stayed continuous during a particular transition.

## Existing diagnostic controls and output

The current diagnostic cvars are aw_cell_change_method (1 is the current default, 2 enables read-ahead), aw_cell_prefetch_kib (128, 256, or 512), and aw_cell_prefetch_seconds (0.5 to 4 seconds; the recorded route used 1.5 seconds).

cell-load-profile.tsv is appended by AW_StreamLoadEnd. Its fields, in order, are model name, method, model-loader read bytes, read calls, read seconds, decode seconds, world seconds, actor seconds, server total seconds, prefix bytes consumed, prefetch read seconds, low/high hunk marks, prefix capacity, bytes filled, worst prefetch read slice, and look-ahead seconds. The scopes overlap, and the file has no event-level prediction or cancellation history.

cell-visible-profile.tsv is appended by AW_StreamPresented. Its fields are model name, method, elapsed transition seconds, requested prefix bytes, and look-ahead seconds. The callback is invoked from host.c after SCR_UpdateScreen returns, so the elapsed-transition field is a callback timing proxy, not a confirmed destination-world draw.

## A useful low-overhead profiler

Add an opt-in, fixed-size in-memory event ring and per-transition counters. Do not allocate, print, or write files in frame, read, decode, or mixer loops. Dump after the transition or on an explicit diagnostic command. Each event should carry a transition sequence number and enough state to join the record to its build/configuration and route.

Record:

- Transition start, source and target regions, predicted target, direction, loading method, prefix capacity, and cache-condition label.
- Prediction changes, prefix fills/copies/consumption, evictions, and explicit cancellation/miss reasons.
- Inclusive durations and counts for model open/seek/read, decode, world construction, actor construction, state restoration/sign-on, destination-world draw, and display update. Keep nested scopes marked as inclusive or exclusive; never total overlapping timers.
- Bytes and calls by file/operation where practical, plus a hunk high-water mark and allocation failures.
- Input-to-first-drawn-frame timestamps, using a generation marker attached to the destination scene and confirmed at the actual draw/display path.
- Transition-scoped music cursor and voice sample/subtitle state, audio service gaps/late counters, view angles, movement state, equipment, hand state, and torch state.

Use an identical route and asset set, alternate candidate/baseline order, and report each direction separately. Separate warm-cache and cold-cache trials. Compare medians, spread, and worst case as well as bytes, prefix reuse, and frame stalls. Start with a small balanced sample, then extend it if variability is comparable to the observed difference. Run the profiler separately from final timing if its counters measurably perturb the transition.

## Questions for an independent optimizer review

1. Which minimal counters distinguish a useful prefix that was cancelled, evicted, consumed, or simply irrelevant to the next region?
2. How would you separate guest file-call time, cache behavior, and decoded-model work without claiming physical-device latency?
3. What is the least intrusive reliable marker that proves the destination world was drawn and displayed?
4. Which matched-route design gives enough confidence to distinguish a 30 ms effect from ordering, workload, and cache variation?
5. What state and audio continuity checks should be mandatory before accepting a faster transition?

## Acceptance still required

Extend the matched native route on the patched candidate and unchanged baseline beyond the initial two samples per direction. Include ordinary walking, both directions, narrow/corner boundaries, and repeated transitions. Confirm correct region selection and prefix use, actual destination-world presentation timing, frame cost and memory headroom, and preserved view/equipment/hand/torch state. Test active voice and music continuity during the same transitions. Keep the default unchanged until the data show a repeatable benefit without regressions.

See the [performance bug entry](../BUG_JOURNAL.md#perf-readahead-29-cell-crossing-pauses-and-premature-prefetch-cancellation) for the project tracking status.