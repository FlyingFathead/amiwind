#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Create private NPC/door/container inventories from an owned base master."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external,resolve_data_files,child_ci
from mwad.vicinity import region_audit,roster_markdown

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--center',type=int,nargs=2,default=(-2,-9),metavar=('X','Y'))
    p.add_argument('--radius',type=int,default=1)
    a=p.parse_args();data=resolve_data_files(a.data_files);out=ensure_external(a.out,'private area audit')
    if out.exists():p.error('Output exists; use a new checkpoint directory')
    report=region_audit(child_ci(data,'Morrowind.esm').read_bytes(),a.center,a.radius)
    out.mkdir(parents=True,exist_ok=False)
    (out/'vicinity-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SEYDA_NEEN_CAST.md').write_text(roster_markdown(report))
    print(json.dumps({'cells':len(report['cells']),'counts':report['counts'],'warnings':report['warnings']},indent=2))
if __name__=='__main__':main()
