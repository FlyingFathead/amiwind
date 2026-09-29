# v0.0.23-dev3 tester feedback — 29 September 2026

Recorded from the owner's playtest, including the follow-up layout and rider
reports. Dates use Europe/Helsinki. Published dev3: commit
`7e36e9051da477147f78cf22236a0a4c0c7201ae`, successful CI run 36601097418;
owner log confirms tag, prerelease creation and downloaded-asset verification.

| Report | dev4 response |
| --- | --- |
| Logo fades too quickly; theme starts late | Two-second fade in, five-second hold, one-second fade out. Theme starts with the logo and continues into the menu. Space, Enter and Esc skip branding. |
| First prophecy quote has unreadable burned-in lettering again | Optional privately supplied first quote is rasterized with the owned converted font into a small sidecar. `aw_intro_text_overlay 1` selects it; `0` shows the original video. Normal video/audio are retained. The playtests include the restored opening quote. |
| Name-entry caret appears as a ball | Draw a vertical line directly, independent of ornamental font glyphs. |
| Two dialogue rows have uneven vertical spacing | Measure the complete visible glyph block and center it vertically; center each line horizontally without stretching spaces. |
| A short reply such as “Yes?” wastes a full-width box | New default `aw_dialogue_box_layout 3`: fit the widest line and block height, with eight pixels of equal padding and a bottom-centered box. Modes 1 and 2 preserve fixed legacy and centered full-width alternatives. |
| Aim identity is absent during opening speech | The close, unobstructed aim label works during sampled intro speech; prompts, selectors, reading and menus still suppress it. |
| Rotation hints show a skull/tree | Plain `LMB: rotate`; clicking the head preview rotates it. Existing keyboard rotation remains available. |
| Tree cut off at `-71 -429 38 / 262 / -7` | Reproduced natively. Signed/unsigned sprite depth comparison rejected pixels over the negative-depth background. Correct signed comparison preserves solid-wall occlusion and transparent texels. |
| Port “rock of woe” | **Owner confirms fixed in dev3.** Preserve the corrected transforms and low-poly rock conversion. |
| Darvame Hleran missing beside the Strider | Exported placement existed, but floor placement ran before later static platform brushes spawned. Delay actor floor placement until scenery is linked. Native origin changes from ground z≈63 to platform z≈205 at the original x/y. |

## Trials and errors

Turning distance culling off made the complete tree visible. That initially
suggested the brush/leaf ordering path. A trial that refreshed culled-leaf sort
keys did not repair the tree and was discarded. The tree is an alpha sprite,
not a brush mesh: negative background depth was promoted to unsigned during its
pixel comparison. A production-routine test fails before the comparison fix and
passes afterward, while checking nearer-wall occlusion and transparent pixels.
The existing dev3 house/brush fix is retained without that experimental rewrite.

Darvame was present in source, exported entities and runtime diagnostics. The
missing-rider symptom was floor-placement order, not another draw-list capacity
problem. All residents use the corrected deferred floor-placement path. Existing
Census/interior collision coverage still needs exhaustive owner inspection.

See [dev4 evidence](RELEASE-v0.0.23-dev4.md). Previously open issues, including
pier/deck containment, door squeaks and complete voice behaviour, remain open.
