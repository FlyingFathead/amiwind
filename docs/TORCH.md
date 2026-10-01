# Placeholder carried torch

Press **F** to raise the hands, then **V** (`aw_torch`) to toggle the torch.
V can select it during the draw animation; illumination begins when the hands
are fully raised. Press V again to put it away, or F to lower the hands and
extinguish it. Shift+V retains the existing draw-distance shortcut. Personal
key bindings may override the shipped V default.

This prototype combines a small palette-coloured shaft/flame overlay with one
keyed, monochrome Quake dynamic light. Its radius flickers deterministically
between 141 and 148 native units. The light originates at the view position;
it is not a directional flashlight or a shadow-casting light. In particular,
nearby thin walls do not guarantee light occlusion. The software renderer makes
surfaces brighter; the flame colours do not turn the illumination orange.

Torch selection is preserved through ordinary door and world-region crossings.
Lowering the hands, death and leaving gameplay disable its light. The current
save/new-game hand reset also resets torch selection. Punching is suppressed
while the torch is equipped. The viewmodel visibility setting, chase camera
and very wide FOV can hide the first-person overlay without changing whether
the equipped torch illuminates the world.

The renderer now transforms dynamic-light origins into each translated/rotated
brush model's local coordinates, both when marking surfaces and building their
light contribution. Converted cave pieces need this same transform as world
geometry. Other dynamic lights use the correction too; water rendering is
unchanged.

## Validation and limits

Native tests exercise F/V state transitions through compiled project QuakeC,
death/lowering, normal fist attacks, one-light reuse, viewport clipping,
actual software surface illumination, and translated/rotated brush lighting.
The 68040/FPU engine compiles with this feature. These checks do not establish
Amiga frame rate, flame appearance, natural cave visibility or acceptable cache
cost. Compare the same cave camera with the torch off/on on the target emulator
before treating it as performance-accepted.

There is no inventory item, fuel, durability, NPC torch equipment, coloured
lighting or original Morrowind torch model yet. Those remain future equipment
and lighting work; this is an explicitly temporary visibility aid.
