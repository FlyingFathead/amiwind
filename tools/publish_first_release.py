#!/usr/bin/env python3
"""Owner-run first GitHub release. Check locally by default; --publish opts in."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from project_version import ROOT, VERSION
from release import inspect_source, validate_candidate

REPOSITORY = 'FlyingFathead/amiwind'


def run(args, capture=False):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=ROOT, check=True,
                          text=True, stdout=subprocess.PIPE if capture else None).stdout


def checked_assets(directory):
    """Only the two public source archives can enter the initial release."""
    if VERSION != '0.0.16':
        raise ValueError('This first-release helper is for v0.0.16 only')
    assets=[]
    for suffix in ('public-source', 'public-source-incremental'):
        path=directory/f'AmiWind-v{VERSION}-{suffix}.zip'
        sidecar=path.with_suffix('.zip.sha256')
        expected=sidecar.read_text().strip().split()
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected != [actual,path.name]:
            raise ValueError('Checksum mismatch: '+str(path))
        assets.extend((path,sidecar))
    validate_candidate(ROOT,assets[0])
    with zipfile.ZipFile(assets[0]) as full, zipfile.ZipFile(assets[2]) as patch:
        names=patch.namelist()
        if len(names)!=len(set(names)) or patch.testzip():
            raise ValueError('Invalid incremental archive')
        for name in names:
            if name not in full.namelist() or patch.read(name)!=full.read(name):
                raise ValueError('Patch differs from the full source: '+name)
        if f'amiwind/docs/PATCH-v{VERSION}.json' not in names:
            raise ValueError('Missing incremental base manifest')
    return assets


def publish(assets):
    for program in ('git','gh'):
        if not shutil.which(program):raise ValueError('Install '+program+' first')
    # Never display authentication tokens or change the selected account.
    login=run(['gh','api','user','--jq','.login'],True).strip()
    if login!='FlyingFathead':raise ValueError('Select the FlyingFathead GitHub account first')
    if not run(['git','config','user.name'],True).strip() or not run(['git','config','user.email'],True).strip():
        raise ValueError('Configure your Git commit name and email first')
    if not (ROOT/'.git').exists():
        run(['git','init','-b','main'])
    if run(['git','branch','--show-current'],True).strip()!='main':
        raise ValueError('Expected main; no branch will be switched automatically')
    remote=subprocess.run(['git','remote','get-url','origin'],cwd=ROOT,text=True,capture_output=True)
    if remote.returncode==0:
        if remote.stdout.strip() not in ('https://github.com/'+REPOSITORY+'.git','git@github.com:'+REPOSITORY+'.git','https://github.com/'+REPOSITORY):
            raise ValueError('origin points to a different repository')
        info=json.loads(run(['gh','repo','view',REPOSITORY,'--json','isPrivate'],True))
        if not info['isPrivate']:raise ValueError('Initial workflow expects a private repository; visibility will not be changed')
    else:
        # Fails safely if a remote already exists; never recreates/replaces it.
        run(['gh','repo','create',REPOSITORY,'--private','--source',ROOT,'--remote','origin',
             '--description','AmiWind: an experimental Morrowind demake for Commodore Amiga'])
    inspect_source(ROOT)
    run(['git','add','-A'])
    allowed=set(inspect_source(ROOT))
    tracked=set(run(['git','ls-files','-z'],True).rstrip('\0').split('\0'))
    if tracked != allowed:raise ValueError('Staged/tracked files differ from the public source allowlist')
    dirty=subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT)
    if dirty.returncode==1:
        run(['git','commit','-m','AmiWind v0.0.16: first repository release'])
    elif dirty.returncode!=0:raise ValueError('Cannot inspect staged changes')
    commit=run(['git','rev-parse','HEAD'],True).strip()
    run(['git','push','-u','origin','main'])
    # Wait for this commit's source/dry-run CI; never release an untested later head.
    run_id=None
    for attempt in range(60):
        runs=json.loads(run(['gh','run','list','--repo',REPOSITORY,'--workflow','source-check.yml',
                            '--commit',commit,'--event','push','--json','databaseId,headSha','--limit','5'],True))
        matching=[item for item in runs if item['headSha']==commit]
        if matching:run_id=str(matching[0]['databaseId']);break
        time.sleep(5)
    if not run_id:raise ValueError('CI did not appear; branch is pushed but no tag/release was created')
    run(['gh','run','watch',run_id,'--repo',REPOSITORY,'--exit-status'])
    if run(['git','rev-parse','HEAD'],True).strip()!=commit:
        raise ValueError('Local HEAD changed during CI')
    if run(['git','status','--porcelain'],True).strip():
        raise ValueError('Working tree changed during CI')
    checked_assets(assets[0].parent)
    tag='v'+VERSION
    existing=subprocess.run(['git','rev-parse','--verify','refs/tags/'+tag+'^{commit}'],cwd=ROOT,text=True,capture_output=True)
    if existing.returncode==0:
        if existing.stdout.strip()!=commit:raise ValueError('Existing tag points elsewhere; it will not be moved')
    else:
        run(['git','tag','-a',tag,'-m','AmiWind '+tag+' demo release',commit])
    run(['git','push','origin',tag])
    existing_release=subprocess.run(['gh','release','view',tag,'--repo',REPOSITORY],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if existing_release.returncode==0:raise ValueError('Release already exists; its assets will not be overwritten')
    run(['gh','release','create',tag,*assets,'--repo',REPOSITORY,'--verify-tag','--prerelease',
         '--title','AmiWind '+tag+' — first demo release','--notes-file',ROOT/'docs'/('RELEASE-'+tag+'.md')])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',type=Path,default=ROOT.parent)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    try:
        assets=checked_assets(args.artifacts.resolve())
        print('Public source, incremental contents and checksums verified.')
        if args.publish:publish(assets)
        else:print('Local check only. --publish initializes/pushes the private repository, waits for CI, then tags/releases.')
    except (OSError,ValueError,subprocess.CalledProcessError,zipfile.BadZipFile) as exc:
        parser.exit(1,str(exc)+'\n')


if __name__=='__main__':main()
