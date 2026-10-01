# Reconciled v0.0.25-rc1 source

Combines the original rc1 candidate with recovery checkpoint 006. Original
archives remain unchanged. This is a source handoff for local compilation;
no native executable or private HDF is delivered for this combined source.

Keep original rc1 town ground/water textures, stronger ground-bound checks,
persistent map view and XYZ header, aw_pos global/source-cell output, editable
Alt+M chord, exact twice-Shift noclip velocity and compiler-warning fixes.
Import checkpoint 006 modifier/Focus/Caps repair, launcher executable modes,
five-autosave default, finite-coordinate guard, source audit tool and config
receipt coverage. Map tracking now uses the common source transform each draw.
The compact coordinate rows and compass retain the original validated layout.

Autosaves remain configurable: config/game.cfg supplies aw_autosaves 5; saved
id1/config.cfg overrides it. Console aw_autosaves N and Options > Autosave
history accept 0..16; zero disables automatic saves. Normal exit persists the
setting. Existing user values remain intact. Quicksave generations are separate;
the empty/incompatible save-menu distinction is still unresolved.

Canonical bindings use config/keymaps.cfg and id1/keymaps.cfg. Legacy personal
id1/keymap.cfg is read before the plural file. A later plural file takes priority;
settings remain in config.cfg. Do not copy both sets of source default bindings.
Only one M/N input handler is installed. Alt+M stays gameplay-only and debug-gated.

Earlier native evidence belongs to its exact original executable, not this
merged runtime. Check docs/validation/reconciled-rc1.json for new source checks.
The 23 actor-contact findings and the production image gate remain unchanged.
No merged native runtime or full island rebuild has been run here.

Preserve owner cleanup 9d22f4a: remove docs/images/amiwind-v0.0.24-journal.png
and its packaging exception. Keep the corrected v0.0.25-dev1 journal screenshot.

Remove the obsolete v0.0.24-rc4 journal screenshot as well. The only remaining
journal image is docs/images/amiwind-v0.0.25-dev1-journal.png.

Input preflight and build receipts now ignore personal transfer/backup archives,
including case-colliding Morrowind_Video.zip/Morrowind_video.zip. Actual loose
Video/mw_intro.bik and ESM/BSA validation remain unchanged. See BUG_JOURNAL.md.
