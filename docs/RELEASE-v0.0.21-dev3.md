# AmiWind v0.0.21-dev3 — opening maintenance

- Restore the missing Census room floor/walls from architectural ACTI reference
 172861. Its tutorial script does not make the room optional.
- Correct automatic dock approach distance to compare matching feet positions,
  retaining the source threshold and speech/menu/control gates.
- Render reading pages with black/gray text on a plain light background (the
  current world palette maps requested white to warm off-white); restore menu colours afterward.
- Preserve more Census wall-art detail before the bounded native texture bake.
- Highlight New Game by default in its confirmation from main/pause menus;
  Enter accepts, Esc or selecting Cancel returns. Mouse anchor follows selection.
- Add `npc_interaction_layout_template_001`: small Morrowind name above a
  console-font action, right-aligned immediately below the viewport.
- Accept arrows and WASD in character/menu choices and reader paging.
- Enable draw/punch after hall paper acceptance, independently of the opening
  enclosure; retain menu locks and post-release controls.
- Track the courtyard ring's depletion independently of tutorial stage and
  current player inventory; taking it cannot duplicate it on later visits.
- Add a reusable compiled standing-hull walkability scan with hole/edge reports.
- Add the fixed Y/N/version bug index and retain all new owner reports.

The dev2 invisible-barrier rotation correction remains included. Previous
release archives remain immutable. See BUGS.md and journal J016-J021 for causes,
failed baselines, fixes and verification limits.

Validation: 215 host tests passed. Native compiler warnings decreased from 93 to 87;
no new diagnostics and no warning suppression. The six removed diagnostics were
misleading-indentation warnings in the touched UI/menu code. The final private
image has 477 verified payload files; focused FS-UAE results accompany the build.

Pier escape, the separately reported captain-wing out-of-bounds position,
exterior door/wall overlap, complete natural opening acceptance, generic downstairs door
interaction/animation/audio and both intermittent freezes remain open. A smaller
radius-bounded opening exterior is planned, not implemented in this build.
NPC ambient idle speech is future work. The owner reports character selection
otherwise working reasonably well; that does not close the full opening checklist.

The Census scene data changes the save-content fingerprint. Retain older HDFs
and their saves; this build intentionally refuses incompatible scene-content saves.
