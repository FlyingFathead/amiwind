# In-game action buttons

For UI mode 2, discrete confirmation and selection actions should have visible
rectangular frames in both selected and unselected states. Match the existing
OK button's UI skin and retain a distinct inset selection highlight. Do not
replace key bindings or click targets merely to change their appearance.

The dev4 source candidate frames Go back and Choose in character confirmation,
covering appearance, class, birthsign and final review through their shared
dialog. Silt-strider destination choices and Cancel use the same framed style.
Their action logic is unchanged. UI mode 1 retains its previous presentation.
The main menu and Esc/pause menu are outside this styling change.

Map teleport already has a rectangular outline. Continuous help text, journal
text, reading content and list data are not automatically turned into buttons.
Apply this rule to new in-game action controls as they are implemented.

Target screenshots and legibility at the normal 320x200 resolution still need
acceptance. Source changes and host fixtures do not by themselves close visual
acceptance, mouse usability or a whole-screen layout review.
