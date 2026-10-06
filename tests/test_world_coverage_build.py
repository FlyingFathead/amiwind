# SPDX-License-Identifier: GPL-3.0-only
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_aga
from test_world_asset_coverage import fixture


class WorldCoverageBuildTests(unittest.TestCase):
    def record(self,root,kind):
        record=dict(version='test-build',binary_sha256='a'*64)
        if kind=='image':record['hdf_files']=[dict(file='game.hdf',bytes=123,sha256='b'*64,readback='passed')]
        path=root/('engine-build.json' if kind=='engine' else 'build.json')
        path.write_text(json.dumps(record)+'\n')
        return path,record

    def test_both_build_kinds_save_unknown_footer_and_retain_identity(self):
        for kind in ('engine','image'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                root=Path(td);path,record=self.record(root,kind);stdout=io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    result=build_aga.write_world_coverage(root,kind)
                    repeated=build_aga.write_world_coverage(root,kind)
                self.assertEqual(result,repeated)
                self.assertEqual(result['status'],'unknown');self.assertEqual(result['rows'],[])
                self.assertIn('World coverage unknown',stdout.getvalue())
                updated=json.loads(path.read_text());summary=updated.pop('world_coverage')
                self.assertEqual(record,updated)
                raw=(root/summary['report']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),summary['sha256'])
                self.assertEqual(json.loads(raw),result)
                self.assertEqual(summary['build'],build_aga.world_coverage_build(record,kind))

    def test_matching_evidence_reports_supplied_counts_and_binds_input(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);path,record=self.record(root,'image')
            evidence=fixture();build=build_aga.world_coverage_build(record,'image')
            evidence['build']=build
            for stage in ('maps','installed'):evidence[stage]['build_id']=build['id']
            source=root/'input.json';source.write_text(json.dumps(evidence))
            with contextlib.redirect_stdout(io.StringIO()):result=build_aga.write_world_coverage(root,'image',source)
            self.assertEqual(result['rows'][0]['placements']['exterior']['installed_unique'],1)
            self.assertEqual(json.loads(path.read_text())['world_coverage']['evidence_sha256'],build_aga.digest(source))
            record['hdf_files'][0]['sha256']='c'*64;path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'another build'):
                build_aga.write_world_coverage(root,'image',source)
            self.assertEqual(json.loads(path.read_text()),record)

    def test_both_cli_commands_accept_optional_evidence(self):
        commands=[['engine','--sdk','sdk','--out','out'],
            ['image','--sdk','sdk','--no-npc-gallery','--data-files','owned','--world-scenery','world',
             *[part for name in ('scene','music','media','engine','out','qcc','qbsp','vis','light','xdftool','rdbtool') for part in ('--'+name,name)]]]
        for command in commands:
            for evidence in ([],['--world-coverage','coverage.json']):
                with self.subTest(command=command[0],evidence=bool(evidence)),patch('sys.argv',['build_aga.py',*command,*evidence]),patch.object(build_aga,command[0]) as action:
                    build_aga.main()
                self.assertEqual(action.call_args[0][0].world_coverage,Path('coverage.json') if evidence else None)


if __name__=='__main__':unittest.main()
