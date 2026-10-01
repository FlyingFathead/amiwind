# v0.0.25-dev1 feedback and v0.0.25-rc1 work

Owner reports, 1 October 2026. Candidate name: **v0.0.25-rc1**.
These are acceptance requirements; an item is not fixed merely because it is listed.

- Priority 1: connect detailed Seyda Neen to the main island terrain, preserving
  detailed Balmora and the frozen polygon-survey subdivisions. Check ordinary
  walking across the boundaries; a noclip placement beyond the edge is insufficient.
- Show universal source XYZ and runtime-local XYZ in the compact console font.
  The map marker must use the same source position and follow movement/rebasing.
- Add a compass to the normal gameplay HUD, without enabling debug overlays.
- Investigate grey valley surfaces and apparent flooding. The reported local
  camera is `9 484 102`, yaw `298`, pitch `50`; its terrain region was not recorded.
  Check original LAND heights, source water policy and region Z origins before
  changing the water datum. Map curvature and a Seyda-derived sea level are
  owner hypotheses, not established causes.
- M and N send the game behind the AmigaDOS screen, including when typing in
  the debug console. Preserve plain letters; deliberate desktop access should
  use Alt+M in debug mode. Test actual native input before claiming resolution.
- Ctrl movement in debug noclip should be twice the speed reached with Shift,
  including sideways/vertical movement, with no extra diagonal acceleration.
- Keep editable keymaps in a separate configuration file and maintain a command
  and shortcut list, including reserved panel/console controls and debug gates.
- Record original-game unexplored-map masking as a TODO. Do not implement it
  in this candidate.

The owner considers the M map's appearance successful. Preserve that presentation
while fixing its position indicator and controls.
