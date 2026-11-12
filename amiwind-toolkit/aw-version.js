// SPDX-License-Identifier: GPL-3.0-or-later
// The AmiWind version this Toolkit ships with: the VERSION file of the build, copied here when the version changes
// (tools/toolkit_version.py stamp) and checked against VERSION by tools/tracker_version_check.py. Every export of the
// Toolkit pages (the inspector's JSON copies, the World Map state) carries this value as its "version"; nothing else
// in the pages types a version number. The Toolkit's own counter is a separate field, "toolkit_build".
(function (root) {
  root.AMIWIND_VERSION = '0.0.65';
})(typeof window !== 'undefined' ? window : this);
