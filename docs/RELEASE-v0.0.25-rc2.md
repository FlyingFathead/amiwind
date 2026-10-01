# AmiWind v0.0.25-rc2 — source reconciliation and input discovery

Source release candidate for local compilation. Incorporates the original rc1,
recovery checkpoints 001/004/006 and the owner's screenshot cleanup. No private
playable, native rc2 binary or complete rc2 image is delivered with this source.

- Match original Morrowind.esm/Morrowind.bsa by name, locate Data Files beneath
  the selected root, and accept supported assets in known game folders. Ignore
  remote-work ZIPs and unrelated files before validation and build hashing.
  The actual intro is Video/mw_intro.bik; transfer archives are never needed.
- Retain corrected Seyda handoff, both detailed towns, adaptive shorelines and
  original town ground/water textures. Keep the recovered polymap subdivisions.
- Combine shared live coordinates with persistent map zoom/pan, global/local HUD,
  compass and aw_pos source coordinates. Keep unexplored-map masking deferred.
- Keep M/N screen protection and debug/gameplay-only editable Alt+M. Import
  qualifier/Shift/Caps/focus repair and retain twice-Shift Ctrl noclip motion.
- Default to five autosaves. aw_autosaves remains configurable 0..16 through
  config.cfg, the console and Options; zero disables it. Saved preferences win.
- Preserve executable launcher modes and separate personal keymaps, including
  reading the checkpoint's singular keymap.cfg before the canonical keymaps.cfg.
- Keep only docs/images/amiwind-v0.0.25-dev1-journal.png; remove the obsolete
  v0.0.24 and v0.0.24-rc4 journal pictures, links and packaging entries.

The reconciliation and source choices are recorded in RECONCILE-v0.0.25-rc1.md;
new builder regression details are in BUG_JOURNAL.md. Host checks and archive
identity are recorded in validation/rc2-source.json. Earlier native screenshots
and walking/input/HDF evidence remain evidence for their original executable,
not a claim that rc2 has been run natively. The owner compiles and validates rc2.

The 23 existing strict NPC contact findings still block the normal production
image gate. No thresholds or acceptance gates were weakened. Quicksave ordering
and the menu's absent/corrupt/incompatible distinction remain open; autosave
retention does not implement multiple quicksave slots. Full-island walking and
physical Amiga validation remain outstanding. See LOCAL-RC2.md for commands.
