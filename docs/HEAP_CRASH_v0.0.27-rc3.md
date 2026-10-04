# Heap crash report: v0.0.27-rc3 Seyda Neen load

Incident: CRASH-01. Status: **OPEN — no verified fixed build**.
Recorded/updated: 3 October 2026. The repair source is included in published
[v0.0.27](RELEASE-v0.0.27.md); the stable private image passed static gates and
HDF readbacks. Exact-route target verification remains open.

## 1. Version, bug, location and circumstances

Affected build: local AmiWind v0.0.27-rc3 town-handoff candidate, image-002,
played in WinUAE using its generated rc3 configuration. The reference configuration
has 16 MiB Fast RAM; the engine reserves an 11 MiB hunk heap (11534336 bytes).

While in Jiub's opening/name-entry scene, the owner entered `dbg aw hors 0`,
which normally takes the player to Seyda Neen. The game showed a brief loading
screen and exited to AmigaDOS. WinUAE remained open. The prompt showed the
startup “Loading AmiWind v0.0.27-rc3” text followed by `1>` without an immediate
on-screen fatal reason. Detached-filesystem inspection recovered ERROR.TXT:

```
Hunk_Alloc sn012: need 2767120 bytes, free 1682208 of 11534336
```

Impact: the restart/load path failed in the original rc3 candidate and blocked
its acceptance. Later publication does not retroactively close this target incident.
Other headroom failures are identified by estimates, not claimed as reproduced
crashes. See [all 28 map profiles](MAP_MEMORY_PROFILE.md).

Introducing content change: rc3 expanded the Seyda Neen real-terrain apron and
subdivision render coverage to address the rc2 town/world handover gap. sn012
BSP bytes increased from 5507736 to 8395232; its visibility lump increased from
473407 to 2767103 bytes. The rocks/mushrooms already worked in the earlier
playtest; this later terrain-coverage change exposed the loading failure.

Established allocation mechanism: AW_LoadBrushSection buffered visibility input
in high-hunk temporary storage, then Mod_LoadVisibility requested a second full
resident copy in the low hunk. The copies coexisted and the second allocation
failed. This duplicate-copy loader behavior predates rc3; its first introducing
version is unverified. Held-input/gameplay-state preservation did not create this
BSP/visibility expansion and is not the established cause.

## 2. How to replicate

1. Use the affected original rc3 image-002 and its generated WinUAE configuration;
   record the image/binary hashes and emulator settings before testing. Do not
   substitute a repaired engine and call that a reproduction of the original.
2. Start a new game and reach Jiub's name-entry scene.
3. Open the debug console and enter `dbg aw hors 0`.
4. Observe the brief loading screen followed by return to AmigaDOS rather than
   successful Seyda Neen entry. WinUAE itself stays running.
5. Preserve ERROR.TXT and confirm the sn012 allocation failure above. The affected
   minimal boot image lacks the AmigaDOS Type command, so detach the HDF before
   inspecting its filesystem with host tools. Never modify/read through a second
   writable mount while the emulator owns the image.

Observed by the owner and supported by the recovered fatal report. Repetition
count and exact emulator executable revision were not separately recorded;
therefore deterministic repetition across other configurations is not claimed.

## 3. How to fix, and what remains open

The duplicate-copy repair was introduced during rc3 and is included in v0.0.27:
visibility, lighting and entity byte lumps load directly into final hunk storage.
No geometry, UV or collision simplification is involved in that loader correction.
A real-loader regression checks the 2767103-byte visibility size, byte identity,
absence of a full temporary copy, pack-member-relative offsets and malformed/
truncated input. The loader regression passed and the repaired Amiga engine
compiled. Fatal exits also print their reason and retain ERROR.TXT when writable.

**Those checks do not establish a complete fix for this incident.** The
historical unbounded sn012 estimate after the loader-only repair was 10860976
bytes at loading peak, before the 3 MiB non-BSP reserve and 2 MiB safety margin:
4569520 bytes short under that policy. Later bounded town conversion and the
complete 2,717-map package passed the unchanged static gate. Eliminating the immediate
failed allocation does not prove later map, actor, cache or renderer work fits.

Repair and remaining verification steps:

1. Reduce the actual runtime working set and/or loading peaks for heavy maps.
   Profile geometry, collision, textures, visibility and retained parent data;
   subdivide where useful while preserving all required scenery and seams.
2. Audit every final runtime map with the matching target ABI and unchanged
   positive reserves. A second HDF supplies storage, not additional heap.
3. Profile the entire outgoing/unload/new-load/restoration/first-frame cycle,
   including cache pressure, zone fragmentation and external Fast/Chip memory.
4. Use the assembled stable private image to repeat this exact Jiub-to-Seyda
   route, then test automatic crossings, both directions, restart and save/load.
5. Record the verified fixed version and target evidence only after acceptance.

Repair source version: published v0.0.27, following rc3/rc4/rc5 corrections.
Replacement private image: assembled with both HDF filesystem readbacks passed.
Verified target-fixed version: **pending**. No cold/warm lifecycle trace or
exact-route target acceptance is recorded.

A separate extra-HDF streaming lookup issue is documented as MEM-EXTRA-HDF in
[the bug journal](BUG_JOURNAL.md); do not conflate its potential full-file
fallback peak with the recovered sn012 duplicate-copy crash.

## Producer's note: mitigation is NOT a fix

**Mitigation is a bandage.** A workaround, avoiding a command, lowering settings,
dropping required scenery or increasing emulator RAM may reduce exposure without
correcting the underlying failure. Record mitigation separately; never relabel
it as a fix or use it to close an incident.

A partial correction must also remain distinct from resolving the whole bug.
The direct-byte loader corrects one allocation inefficiency, but this crash
report remains open until the intended content and transition succeed on the
reference target with adequate headroom. Preserve affected/introduced/repair/
verified-fixed versions and reproduction evidence; keep the journal and release
state current so the same regression is not rediscovered without its history.

See [memory allocation](MEMORY_ALLOCATION.md) and
[the heap-watcher lifecycle](HEAP_WATCHER.md).
