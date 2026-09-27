import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import publish_first_release as pub


class FirstRelease(unittest.TestCase):
    def simulate(self, fail_ci=False, login='FlyingFathead'):
        calls=[]
        def command(args,capture=False):
            args=list(map(str,args));calls.append(args)
            if args[:3]==['gh','api','user']:return login+'\n'
            if args[:2]==['git','config']:return 'configured\n'
            if args[:2]==['git','branch']:return 'main\n'
            if args[:2]==['git','ls-files']:return 'README.md\0'
            if args[:2]==['git','rev-parse']:return 'abc123\n'
            if args[:3]==['gh','run','list']:return json.dumps([{'headSha':'abc123','databaseId':42}])
            if args[:3]==['gh','run','watch'] and fail_ci:raise subprocess.CalledProcessError(1,args)
            return ''
        def status(args,**kwargs):
            return subprocess.CompletedProcess(args,1,stdout='',stderr='')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);assets=[root/'AmiWind-v0.0.16-public-source.zip',root/'AmiWind-v0.0.16-public-source.zip.sha256',root/'AmiWind-v0.0.16-public-source-incremental.zip',root/'AmiWind-v0.0.16-public-source-incremental.zip.sha256']
            with patch.object(pub,'ROOT',root),patch.object(pub,'run',command),patch.object(pub.subprocess,'run',status),patch.object(pub.shutil,'which',return_value='/mock/tool'),patch.object(pub,'inspect_source',return_value={'README.md':b'public'}),patch.object(pub,'checked_assets',return_value=assets):
                try:pub.publish(assets)
                except (ValueError,subprocess.CalledProcessError):
                    if not fail_ci and login=='FlyingFathead':raise
        return calls

    def test_failed_ci_cannot_tag_or_release(self):
        calls=self.simulate(fail_ci=True)
        self.assertTrue(any(c[:3]==['gh','run','watch'] for c in calls))
        self.assertFalse(any(c[:2]==['git','tag'] or c[:3]==['gh','release','create'] for c in calls))

    def test_release_contains_only_explicit_public_assets_after_ci(self):
        calls=self.simulate()
        ci=next(i for i,c in enumerate(calls) if c[:3]==['gh','run','watch'])
        tag=next(i for i,c in enumerate(calls) if c[:2]==['git','tag'])
        release=next(c for c in calls if c[:3]==['gh','release','create'])
        self.assertLess(ci,tag)
        self.assertEqual(len([x for x in release if x.endswith('.zip')]),2)
        self.assertFalse(any('private-playable' in x or x.endswith(('.hdf','.rom')) for x in release))

    def test_wrong_account_stops_before_repository_changes(self):
        calls=self.simulate(login='someone-else')
        self.assertEqual(len(calls),1)
