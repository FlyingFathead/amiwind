# First repository release: v0.0.16

The owner runs this workflow on Linux or WSL. It creates a **private** repository
at `FlyingFathead/amiwind`, pushes `main`, waits for that commit's GitHub Actions
source/asset-free build to succeed, then creates tag `v0.0.16` and a demo
prerelease. The release uploads only the full and incremental public source ZIPs
and their checksums. The private playable archive stays on your machine.

Install/configure Git and GitHub CLI and sign in as FlyingFathead beforehand.
Git needs your normal commit name/email. The helper checks the active GitHub
account without printing tokens. It does not install dependencies, switch
accounts, force-push, change repository visibility or replace existing releases.

Download the full and incremental source ZIPs plus their `.sha256` sidecars into
`/path/to/downloads/`. For the first initialization, start with a fresh `amiwind/`
directory. The block below preserves an existing non-Git directory under a
timestamped backup name before extracting. It stops if amiwind/ already contains
a Git repository; use the resume instructions in that case. Do not extract the
private playable here.

```bash
(
  set -euo pipefail
  cd /path/to/downloads
  sha256sum -c AmiWind-v0.0.16-public-source.zip.sha256
  sha256sum -c AmiWind-v0.0.16-public-source-incremental.zip.sha256
  if [ -e amiwind/.git ]; then
    echo 'amiwind/ is already a Git repository; use the resume instructions.' >&2
    exit 1
  fi
  if [ -e amiwind ] || [ -L amiwind ]; then
    backup="amiwind-before-v0.0.16-$(date -u +%Y%m%dT%H%M%SZ)"
    test ! -e "$backup"
    mv -T -- amiwind "$backup"
    echo "Previous directory preserved as $backup"
  fi
  unzip AmiWind-v0.0.16-public-source.zip
  cd amiwind
  python3 tools/publish_first_release.py --artifacts .. --publish
)
```

`--publish` is the explicit opt-in to the Git/GitHub operations. Without it,
the helper verifies local release files only. It uses `git add -A` followed by
an exact public-file allowlist comparison before committing. It stops on any
error. A failed CI run leaves the source pushed for inspection but creates no
new tag or release. Fix the reported failure before retrying.

To resume after a failure, rerun the helper from `/path/to/downloads/amiwind/`;
do not rerun the fresh-extraction block. If the remote already existed before
initialization, verify it is the intended private repository and configure its
`origin` locally; the helper does not merge unrelated history automatically.

The GitHub-created automatic source downloads may use GitHub's own directory
naming. The explicitly attached `AmiWind-v0.0.16-public-source.zip` is the
artifact that guarantees extraction into `amiwind/`.

Extract `AmiWind-v0.0.16-private-playable.zip` into a new directory outside the
repository, for example `/path/to/downloads/amiwind-private/v0.0.16/`. It contains
`AmiWind-v0.0.16.hdf`, `roms/kickstart-3.1-a1200.rom`, private setup instructions
and presets. Play from a writable HDF copy. Do not upload this ZIP to GitHub.

Reference CLI behavior: [repo create](https://cli.github.com/manual/gh_repo_create),
[run watch](https://cli.github.com/manual/gh_run_watch),
[release create](https://cli.github.com/manual/gh_release_create).
The collaborator has not run Git/GitHub publication; this is the owner-run step.
