"""M1 acceptance tests: invalid inputs, cumulative patches, immutable sources.

Run: python3 -m unittest discover -s tests -v
No network, toolchain, device, or third-party Python dependency required.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import profile as p


class ConfigTests(unittest.TestCase):
    def test_all_profiles_and_schemas(self):
        for path in (p.ROOT / 'profiles').glob('*/profile.json'):
            config, profile = p.normalize({}, path.parent.name)
            lock = p.read_json(p.ROOT / 'manifests/locks' / (profile['name'] + '.lock.json'))
            p.validate_lock(lock, config, profile)
            self.assertFalse(p.preflight(config, profile, lock)['release_allowed'])

    def test_legacy_and_normalized_inputs_have_same_identity(self):
        raw = {'ksu_type':'resukisu','susfs_enable':'true','bbr_enable':'false',
               'kernel_suffix':'中文 & / \\ " $(touch sentinel)', 'build_time':'Fri Sep 04 00:00:00 UTC 2026'}
        config, _ = p.normalize(raw)
        again, _ = p.normalize(config)
        self.assertEqual(p.canonical(config), p.canonical(again))
        self.assertEqual(config['identity']['kernel_suffix'], raw['kernel_suffix'])
        self.assertFalse(config['features']['bbr'])

    def test_actions_and_local_flag_adapters_match(self):
        ci, _ = p.normalize({'ksu_type':'resukisu','susfs_enable':True,'lz4_zstd':True,
                             'attribution_enable':False,'build_user':'小澪'})
        local, _ = p.normalize(p.legacy_arguments(['--ksu','resukisu','--susfs','--lz4','--no-attribution','--user','小澪']))
        self.assertEqual(p.digest(ci),p.digest(local))
        with self.assertRaises(p.Invalid):p.legacy_arguments(['--user'])

    def test_reject_illegal_combinations_and_types(self):
        cases = [
            {'ksu_type':'none','susfs_enable':True},
            {'ksu_type':'resukisu','susfs_enable':True,'droidspaces':'standard'},
            {'ksu_type':'resukisu','susfs_enable':True,'droidspaces':'extend'},
            {'ksu_type':'resukisu','susfs_enable':True,'hook_mode':'manual'},
            {'ksu_type':'other'}, {'susfs_enable':'yes'}, {'bbr_enable':1},
            {'droidspaces':False}, {'droidspaces':'unknown'}, {'unknown':True},
            {'bbr':True,'bbr_enable':False}, {'ghost_task':True},
            {'rekernel_enable':True,'release_enable':True},
            {'debug_skip_build':True,'release_enable':True},
            {'debug_skip_build':True,'ccache_update':True},
            {'independent_modules':True}, {'build_user':'a\nb'},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(p.Invalid):p.normalize(case)

    def test_explicit_profile_conflict(self):
        with self.assertRaises(p.Invalid):p.normalize({'ksu_type':'none'},'ace6-resukisu-manual-6.6')

    def test_extend_inherits_standard_without_susfs(self):
        for name in ['ace6-droidspaces-extend-6.6','ace6-droidspaces-resukisu-extend-6.6']:
            config, profile = p.normalize({},name)
            self.assertIn('droidspaces-standard',profile['capabilities'])
            self.assertIn('droidspaces-extend',profile['capabilities'])
            self.assertFalse(config['features']['susfs'])

    def test_unlocked_sources_kpm_and_profile_tampering(self):
        config, profile = p.normalize({})
        lock = p.read_json(p.ROOT/'manifests/locks/ace6-minimal-6.6.lock.json')
        for mutate in [lambda l:l['sources']['kernel'].update(commit='main'),
                       lambda l:l['sources'].pop('modules'),
                       lambda l:l.update(profile_sha256='0'*64),
                       lambda l:l['steps'][0].update(sha256='0'*64),
                       lambda l:l['resources']['clang'].pop('sha256'),
                       lambda l:l['resources']['actions'].update({'actions/checkout':'v4'}),
                       lambda l:l['sources']['kernel'].update(directory='../outside'),
                       lambda l:l['sources']['modules'].update(directory='src/nested')]:
            candidate=copy.deepcopy(lock);mutate(candidate)
            with self.assertRaises(p.Invalid):p.validate_lock(candidate,config,profile)
        config['features']['kpm']=True
        with self.assertRaisesRegex(p.Invalid,'KPM'):p.validate_lock(lock,config,profile)

    def test_susfs_and_optional_features_block_before_download(self):
        for inputs in [{'ksu_type':'resukisu','susfs_enable':True},{'baseband_guard':True},{'lz4kd_enable':True}]:
            config,profile=p.normalize(inputs)
            lock=p.read_json(p.ROOT/'manifests/locks'/(profile['name']+'.lock.json'))
            with tempfile.TemporaryDirectory() as tmp, patch.object(p,'run',side_effect=AssertionError('must not run commands')):
                with self.assertRaisesRegex(p.Invalid,'blocked'):p.prepare(config,profile,lock,Path(tmp)/'work')
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_duplicate_keys_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.json';path.write_text('{"bbr":true,"bbr":false}')
            with self.assertRaisesRegex(p.Invalid,'duplicate'):p.read_json(path)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.repo=self.root/'external'
        p.run(['git','init',self.repo])
        (self.repo/'value').write_text('one\n')
        p.run(['git','-C',self.repo,'add','.'])
        p.run(['git','-C',self.repo,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture'])
        self.sha=p.run(['git','-C',self.repo,'rev-parse','HEAD'])
        self.config,self.profile=p.normalize({})
        self.lock=p.read_json(p.ROOT/'manifests/locks/ace6-minimal-6.6.lock.json')
        self.lock['sources']={name:{'url':'https://example.invalid/fixture.git','reference':'fixture',
            'commit':self.sha,'directory':name} for name in ('kernel','modules','devicetrees')}
        self.lock['local_files']=[];self.lock['steps']=[]
        (self.root/'schemas').mkdir()
        for name in ('lock','manifest'):
            (self.root/'schemas'/f'{name}.schema.json').write_bytes((p.ROOT/'schemas'/f'{name}.schema.json').read_bytes())
        self.external={name:str(self.repo) for name in self.lock['sources']}

    def tearDown(self):self.temp.cleanup()

    def add_patch(self,name,old,new):
        path=self.root/name
        path.write_text(f'diff --git a/value b/value\n--- a/value\n+++ b/value\n@@ -1 +1 @@\n-{old}\n+{new}\n')
        h=p.file_hash(path)
        self.lock['local_files'].append({'path':name,'sha256':h})
        self.lock['steps'].append({'source':'kernel','operation':'patch','layer':'integration',
                                   'path':name,'sha256':h,'destination':''})

    def add_link(self, name='link.spec', target='linked', origin='modules:value'):
        path=self.root/name
        path.write_text(origin+'\n')
        h=p.file_hash(path)
        self.lock['local_files'].append({'path':name,'sha256':h})
        self.lock['steps'].append({'source':'kernel','operation':'link','layer':'integration',
                                   'path':name,'sha256':h,'destination':target})

    def prepare(self,name='work'):
        return p.prepare(self.config,self.profile,self.lock,self.root/name,self.external,self.root)

    def test_cumulative_order_repeatability_and_external_unchanged(self):
        self.add_patch('20-first.patch','one','two')
        self.add_patch('00-second.patch','two','three')
        first=self.prepare('first');second=self.prepare('second')
        self.assertEqual((self.root/'first/kernel/value').read_text(),'three\n')
        self.assertEqual((self.repo/'value').read_text(),'one\n')
        self.assertEqual(p.run(['git','-C',self.repo,'status','--porcelain']),'')
        self.assertEqual(first['manifest_id'],second['manifest_id'])
        self.assertEqual([s['path'] for s in first['steps']],['20-first.patch','00-second.patch'])
        self.assertEqual(first['build'],'not-run')
        self.assertEqual(first['artifacts'],[])
        with self.assertRaisesRegex(p.Invalid,'already exists'):self.prepare('first')

    def test_failed_patch_stops_following_steps_and_preserves_source(self):
        self.add_patch('first.patch','one','two')
        self.add_patch('failure.patch','absent','wrong')
        self.add_patch('never.patch','two','three')
        with self.assertRaisesRegex(p.Invalid,'preparation stopped'):self.prepare()
        self.assertFalse((self.root/'work').exists())
        failure=next(self.root.glob('work.preparing-*/failure.json'))
        report=p.read_json(failure)
        self.assertEqual(report['phase'],'failed')
        self.assertEqual(len(report['steps']),2)
        self.assertEqual(report['steps'][0]['status'],'applied')
        self.assertEqual((failure.parent/'kernel/value').read_text(),'two\n')
        self.assertEqual((self.repo/'value').read_text(),'one\n')

    def test_dirty_external_tree_rejected_before_workspace_creation(self):
        (self.repo/'untracked').write_text('user work')
        with self.assertRaisesRegex(p.Invalid,'dirty'):self.prepare()
        self.assertEqual(list(self.root.glob('work*')),[])

    def test_hidden_index_changes_rejected(self):
        p.run(['git','-C',self.repo,'update-index','--assume-unchanged','value'])
        (self.repo/'value').write_text('user work\n')
        with self.assertRaisesRegex(p.Invalid,'assume-unchanged'):self.prepare()

    def test_wrong_sha_and_bad_hash_rejected_without_download(self):
        self.add_patch('first.patch','one','two')
        (self.root/'first.patch').write_text('corrupted')
        with self.assertRaisesRegex(p.Invalid,'hash'):self.prepare()
        self.assertFalse((self.root/'work').exists())
        self.lock['local_files']=[];self.lock['steps']=[]
        self.lock['sources']['kernel']['commit']='0'*40
        with self.assertRaisesRegex(p.Invalid,'HEAD'):self.prepare()

    def test_copy_cannot_escape_workspace(self):
        self.add_patch('file.patch','one','two')
        self.lock['steps'][0].update(operation='copy',destination='../outside')
        with self.assertRaisesRegex(p.Invalid,'unsafe path'):self.prepare()
        self.assertFalse((self.root/'outside').exists())

    def test_link_uses_locked_source_and_stays_relative(self):
        self.add_link()
        self.prepare()
        target=self.root/'work/kernel/linked'
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.read_text(),'one\n')
        self.assertEqual(target.resolve(),(self.root/'work/modules/value').resolve())

    def test_link_spec_rejects_unknown_or_escaping_source(self):
        self.add_link(origin='unknown:value')
        with self.assertRaisesRegex(p.Invalid,'invalid link spec'):
            self.prepare()


if __name__=='__main__':unittest.main()
