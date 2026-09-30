# Horstator's evening notes, 30 September 2026

Progress from Seyda Neen to Balmora has been good, including the optimizations.
The short Loading pauses in Balmora's centre remain disappointing. Investigate
whether assets can enter and leave memory smoothly based on player coordinates.
High polygon counts may contribute, but measure disk reads, decoding, linking,
collision setup and rendering separately before assigning a cause to the pauses.

Carry the lessons and reusable sub-cell approach from Seyda Neen and Balmora to
future towns. Smaller settlements may need fewer subdivisions; use measured
geometry and memory budgets instead of assuming every city needs Balmora's grid.

Explore a topographic map of the entire base world, with the completed towns
and their runtime subdivisions overlaid. Also show the original Morrowind cell
grid so conversion coverage can be inspected cell by cell. Treat this as a world
inventory and planning view; terrain conversion alone does not complete a region.

Begin comprehensive source-to-runtime asset catalogues, especially characters
and creatures. The immediate inspection tool is the character model gallery in
[the RC1 feedback](FEEDBACK-v0.0.24-rc1.md): browse the base game's cast one at a
time, inspect clothing and proportions, and record what converts and renders.
Large catalogues live on disk; only the current inspection model needs residency.

These are retained owner goals. Seamless loading, whole-world terrain and a
complete playable world are not claimed as implemented by recording them here.

## Initial character placement: no repeated floater repairs

Follow [the initial placement workflow](NPC_GROUND_CONTACT.md). Classify what
support an actor is intended to have at initialization, before applying any
terrain correction. Ground residents get a canonical placement computed on the
host against their owning scene; all overlap copies carry that result. The
independent check reads final quantized models and collision, measures initial
idle-pose contact, and blocks packaging on failures. Unknown classifications are
errors. Tarhiel's scripted fall, cliff racers and Vivec's levitating pose are
documented examples of states that must retain their authored behavior.

This places expensive inspection in conversion, with no per-frame grounding
scan on the Amiga. Native checks remain necessary for initialization/restoration
integration. The intended outcome is automated placement with a failing build
for unresolved cases, rather than repeated manual searches for floating actors.
