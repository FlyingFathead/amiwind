# SPDX-License-Identifier: GPL-3.0-only
"""One scratch folder for builder work: never the system temp directory.

Builder stages used to call tempfile with no directory, which puts their files in /tmp. In the build
container /tmp is a size-limited, RAM-backed, noexec tmpfs: a shared object built there cannot be
loaded (CHIM-ZONE-TMP-NOEXEC-33) and a few GiB of raw video frames there exhaust memory
(BUILD-TMP-SCRATCH-33). Anything a stage executes or that can grow large lives under the build's own
workspace instead:

1. AMIWIND_SCRATCH, when set (the builder sets it to RUN/scratch for every stage it starts);
2. else the `near` folder passed by the caller (for example the stage's output folder), under .scratch;
3. else OUT/scratch in the checkout (the default workspace, which is never tracked).

scratch_dir() makes one fresh folder per use. It is removed when the block ends normally and kept when
the block fails, so a failed stage can be inspected (keep_on_failure=False for many tiny per-item
folders). Small transient files written next to their destination (dir=destination.parent) need
no helper. tests/test_build_scratch.py fails if builder code reaches the system temp directory.
"""
import contextlib
import os
import shutil
import tempfile
from pathlib import Path

ENV = 'AMIWIND_SCRATCH'
ROOT = Path(__file__).resolve().parents[1]


def scratch_root(near=None):
    """The folder scratch folders are created in (not created here)."""
    configured = os.environ.get(ENV)
    if configured:
        return Path(configured)
    if near is not None:
        return Path(near) / '.scratch'
    return ROOT / 'out' / 'scratch'


@contextlib.contextmanager
def scratch_dir(prefix='scratch-', near=None, keep_on_failure=True):
    """A fresh scratch folder (Path), removed after success and kept after a failure."""
    root = scratch_root(near)
    root.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=str(root)))
    try:
        yield path
    except BaseException:
        if not keep_on_failure:
            shutil.rmtree(path, ignore_errors=True)
        raise
    else:
        shutil.rmtree(path, ignore_errors=True)


def scratch_file(near=None):
    """An anonymous binary scratch file (tempfile.TemporaryFile) in the scratch folder, not in /tmp."""
    root = scratch_root(near)
    root.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryFile(dir=str(root))


def stage_environment(run):
    """Environment entries that point every stage the builder starts at RUN/scratch.

    An AMIWIND_SCRATCH the caller already set wins (it can name a bigger or faster volume)."""
    if os.environ.get(ENV):
        return {}
    return {ENV: str(Path(run) / 'scratch')}
