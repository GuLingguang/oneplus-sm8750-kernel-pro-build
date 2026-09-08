"""M1 acceptance tests: invalid inputs, cumulative patches, immutable sources.

Run: python3 -m unittest discover -s tests -v
No network, toolchain, device, or third-party Python dependency required.
"""
import copy
import json
import os
import re
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
            {'ksu_type':'resukisu','susfs_enable':True,'hook_mode':'manual'},
            {'ksu_type':'other'}, {'susfs_enable':'yes'}, {'bbr_enable':1},
            {'droidspaces':False}, {'droidspaces':'unknown'}, {'unknown':True},
            {'bbr':True,'bbr_enable':False}, {'ghost_task':True},
            {'debug_skip_build':True,'release_enable':True},
            {'debug_skip_build':True,'ccache_update':True},
            {'independent_modules':True}, {'build_user':'a\nb'},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(p.Invalid):p.normalize(case)

    def test_main_release_composes_features_and_keeps_runtime_gates_soft(self):
        config, profile = p.normalize({
            'ksu_type': 'resukisu', 'susfs_enable': True, 'lz4_zstd': True,
            'lz4kd_enable': True, 'show_all_algos': True, 'zram_writeback': True,
            'droidspaces': 'extend', 'baseband_guard': True, 'cve_patch': True,
            'better_net': True, 'bbr_enable': True, 'rekernel_enable': True,
            'release_enable': True, 'ccache_debug': True, 'artifact_mode': 'ak3',
        })
        self.assertEqual(profile['name'], 'ace6-main-release-compat-6.6')
        lock = p.read_json(p.ROOT / 'manifests/locks' / (profile['name'] + '.lock.json'))
        report = p.preflight(config, profile, lock, phase='build')
        self.assertTrue(report['prepare_allowed'])
        self.assertFalse(report['release_allowed'])
        self.assertTrue(report['warnings'])
        self.assertFalse(report['blockers'])

    def test_explicit_profile_conflict(self):
        with self.assertRaises(p.Invalid):p.normalize({'ksu_type':'none'},'ace6-resukisu-manual-6.6')

    def test_extend_inherits_standard_without_susfs(self):
        for name in ['ace6-droidspaces-extend-6.6','ace6-droidspaces-resukisu-extend-6.6']:
            config, profile = p.normalize({},name)
            self.assertIn('droidspaces-standard',profile['capabilities'])
            self.assertIn('droidspaces-extend',profile['capabilities'])
            self.assertFalse(config['features']['susfs'])

    def test_extend_preserves_base_features_and_capabilities(self):
        pairs = [
            ('ace6-droidspaces-standard-6.6', 'ace6-droidspaces-extend-6.6'),
            ('ace6-droidspaces-resukisu-standard-6.6', 'ace6-droidspaces-resukisu-extend-6.6'),
        ]
        for base_name, extend_name in pairs:
            base_config, base_profile = p.normalize({}, base_name)
            extend_config, extend_profile = p.normalize({}, extend_name)
            for key, value in base_config['features'].items():
                if key != 'droidspaces':
                    self.assertEqual(extend_config['features'][key], value)
            self.assertEqual(extend_config['features']['droidspaces'], 'extend')
            self.assertTrue(set(base_profile['capabilities']) <= set(extend_profile['capabilities']))

    def test_rekernel_keeps_normalized_toggle_and_manual_base(self):
        config, profile = p.normalize({}, 'ace6-rekernel-experimental')
        self.assertTrue(config['features']['rekernel'])
        self.assertEqual(profile['extends'], 'ace6-resukisu-manual-6.6')
        base = p.profile('ace6-resukisu-manual-6.6')
        self.assertTrue(set(base['capabilities']) <= set(profile['capabilities']))
        lock = p.read_json(p.ROOT / 'manifests/locks/ace6-rekernel-experimental.lock.json')
        report = p.preflight(config, profile, lock, phase='build')
        self.assertTrue(report['prepare_allowed'])
        self.assertTrue(any('T13' in warning for warning in report['warnings']))

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
        for inputs in [{'baseband_guard':True},{'lz4kd_enable':True}]:
            config,profile=p.normalize(inputs)
            lock=p.read_json(p.ROOT/'manifests/locks'/(profile['name']+'.lock.json'))
            with tempfile.TemporaryDirectory() as tmp, patch.object(p,'run',side_effect=AssertionError('must not run commands')):
                with self.assertRaisesRegex(p.Invalid,'blocked'):p.prepare(config,profile,lock,Path(tmp)/'work')
                self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_susfs_inline_source_preparation_is_unblocked(self):
        config,profile=p.normalize({'ksu_type':'resukisu','susfs_enable':True})
        lock=p.read_json(p.ROOT/'manifests/locks'/(profile['name']+'.lock.json'))
        self.assertTrue(p.preflight(config,profile,lock)['prepare_allowed'])

    def test_duplicate_keys_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.json';path.write_text('{"bbr":true,"bbr":false}')
            with self.assertRaisesRegex(p.Invalid,'duplicate'):p.read_json(path)


class CompressionContractTests(unittest.TestCase):
    def test_compression_patches_are_real_and_versioned(self):
        lz4 = (p.ROOT/'patches/split/02_lz4.patch').read_text()
        zstd = (p.ROOT/'patches/split/03_zstd.patch').read_text()
        lz4kd = (p.ROOT/'patches/split/04_lz4kd.patch').read_text()
        self.assertGreater(len(lz4.splitlines()), 2500)
        self.assertGreater(len(zstd.splitlines()), 20000)
        self.assertEqual(len(re.findall(r'^diff --git ', zstd, re.MULTILINE)), 57)
        self.assertIn('-#define ZSTD_VERSION_RELEASE  2', zstd)
        self.assertIn('+#define ZSTD_VERSION_RELEASE  7', zstd)
        self.assertIn('CONFIG_CRYPTO_LZ4KD', lz4kd)
        self.assertIn('config ZRAM_DEF_COMP_LZ4KD', lz4kd)

    def test_build_entrypoints_close_feature_symbols_explicitly(self):
        entrypoints = [p.ROOT/'scripts/build.py']
        required = [
            'CONFIG_TCP_CONG_BBR', 'CONFIG_DEFAULT_BBR', 'CONFIG_IP_SET',
            'CONFIG_BPF_STREAM_PARSER', 'CONFIG_IP6_NF_NAT',
            'CONFIG_ZRAM_WRITEBACK', 'CONFIG_ZRAM_MEMORY_TRACKING',
            'CONFIG_ZRAM_TRACK_ENTRY_ACTIME', 'CONFIG_CRYPTO_LZ4HC',
            'CONFIG_CRYPTO_842', 'CONFIG_ZRAM_DEF_COMP_LZORLE',
        ]
        for path in entrypoints:
            text = path.read_text()
            with self.subTest(path=path):
                for symbol in required:
                    self.assertIn(symbol, text)
                self.assertIn('"lzo-rle"', text)
                self.assertIn('"lz4kd"', text)
        self.assertIn('scripts/build.py', (p.ROOT/'reproduce.sh').read_text())
        self.assertIn('scripts/build.py', (p.ROOT/'.github/workflows/build.yml').read_text())

    def test_zram_registration_contract_names_all_backends(self):
        patch = (p.ROOT/'patches/split/04_lz4kd.patch').read_text()
        for name in ('lzo', 'lzo-rle', 'lz4', 'lz4hc', 'lz4k', 'lz4kd',
                     'deflate', '842', 'zstd'):
            with self.subTest(name=name):
                self.assertIn('"' + name + '"', patch)

    def test_common_build_dry_run_validates_feature_lock_without_download(self):
        result = subprocess.run(
            [sys.executable, 'scripts/build.py', '--lz4', '--lz4kd', '--bbg', '--dry-run'],
            cwd=p.ROOT, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['profile'], 'ace6-minimal-6.6')
        self.assertEqual(len(report['optional_patches']), 4)
        self.assertRegex(report['feature_lock_id'], r'^[0-9a-f]{64}$')

    def test_common_local_and_workflow_dry_runs_share_identity(self):
        base = {
            'ACE6_KSU_TYPE': 'none', 'ACE6_SUSFS': 'false', 'ACE6_LZ4_ZSTD': 'false',
            'ACE6_LZ4KD': 'false', 'ACE6_SHOW_ALL_ALGOS': 'false', 'ACE6_ZRAM_WRITEBACK': 'false',
            'ACE6_DROIDSPACES': 'false', 'ACE6_BASEBAND_GUARD': 'false', 'ACE6_CVE_PATCH': 'false',
            'ACE6_BETTER_NET': 'false', 'ACE6_BBR': 'false', 'ACE6_KPM': 'false',
            'ACE6_REKERNEL': 'false', 'ACE6_KERNEL_SUFFIX': '', 'ACE6_ATTRIBUTION_ENABLE': 'true',
            'ACE6_BUILD_USER': 'Lingguang', 'ACE6_BUILD_HOST': 'kernel-builder', 'ACE6_BUILD_TIME': '',
            'ACE6_TAG': '', 'ACE6_RELEASE_ENABLE': 'false', 'ACE6_CCACHE_UPDATE': 'false',
            'ACE6_CCACHE_DEBUG': 'false', 'ACE6_DEBUG_SKIP_BUILD': 'false', 'ACE6_CCACHE_ENABLE': 'true',
            'ACE6_INDEPENDENT_MODULES': 'false', 'ACE6_GHOST_TASK': 'false', 'ACE6_ARTIFACT_MODE': 'ak3',
        }
        env = dict(os.environ, **base)
        local = subprocess.run([sys.executable, 'scripts/build.py', '--dry-run'], cwd=p.ROOT,
                               text=True, capture_output=True, env=env)
        workflow = subprocess.run([sys.executable, 'scripts/build.py', '--workflow', '--dry-run'], cwd=p.ROOT,
                                  text=True, capture_output=True, env=env)
        self.assertEqual(local.returncode, 0, local.stderr)
        self.assertEqual(workflow.returncode, 0, workflow.stderr)
        self.assertEqual(json.loads(local.stdout)['config_id'], json.loads(workflow.stdout)['config_id'])
        self.assertEqual(json.loads(local.stdout)['lock_id'], json.loads(workflow.stdout)['lock_id'])

    def test_identity_special_text_is_literal_and_filename_mapping_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / 'sentinel'
            value = f'中文 & / \\ " $(touch {sentinel})'
            result = subprocess.run(
                [sys.executable, 'scripts/build.py', '--user', value, '--suffix', 'perf/$(touch ' + str(sentinel) + ')', '--dry-run'],
                cwd=p.ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(sentinel.exists())
            self.assertEqual(report['identity']['display']['build_user'], value)
            self.assertNotIn('/', report['identity']['filename']['user'])
            self.assertNotIn('/', report['identity']['filename']['suffix'])


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
