#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_bin=${AMIWIND_PYTHON:-python3}
if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "Python 3.10+ is required. See docs/LINUX_BUILD.md." >&2
    exit 1
fi
exec "$python_bin" "$project_dir/tools/build.py" "$@"
