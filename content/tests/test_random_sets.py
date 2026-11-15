"""Verify actual freestanding sampler: bounds, repeatability and stat formula."""
import ctypes
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'content/tools'))
from generate_rules import DEFAULT, generate, validate, header


class SharedSet(ctypes.Structure):
    _fields_ = [('state', ctypes.c_uint32), ('moves', ctypes.c_uint16 * 4),
                ('stats', ctypes.c_uint16 * 6), ('pp', ctypes.c_uint8 * 4),
                ('ivs', ctypes.c_uint8 * 6), ('evs', ctypes.c_uint8 * 6),
                ('nature', ctypes.c_uint8), ('archetype', ctypes.c_uint8)]


def expected_stats(base, ivs, evs, nature, level):
    result = [(2*b + i + e//4)*level//100 + (level+10 if n == 0 else 5)
              for n, (b, i, e) in enumerate(zip(base, ivs, evs))]
    order = [1, 2, 5, 3, 4]
    if nature//5 != nature % 5:
        result[order[nature//5]] = result[order[nature//5]]*110//100
        result[order[nature % 5]] = result[order[nature % 5]]*90//100
    return result


class RandomSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.data = validate(json.loads(DEFAULT.read_text()))
        generate(DEFAULT, cls.folder)
        compiler = shutil.which('gcc')
        if not compiler:
            raise unittest.SkipTest('Host GCC needed for the actual C sampler')
        lib = cls.folder / ('random_sets.dll' if sys.platform == 'win32' else 'random_sets.so')
        subprocess.run([compiler, '-O2', '-shared', '-fPIC', '-I', str(cls.folder),
                        str(ROOT / 'content/tools/random_sets.c'), '-o', str(lib)], check=True)
        cls.lib = ctypes.CDLL(str(lib))
        cls.lib.shared_generate.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(SharedSet)]
        cls.lib.shared_generate.restype = ctypes.c_uint32

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def sample(self, profile, seed, level=50):
        result = SharedSet()
        self.assertEqual(self.lib.shared_generate(profile, seed, level, ctypes.byref(result)), 1)
        return result

    def test_all_profiles_cover_pool_without_duplicates_or_invalid_stats(self):
        for profile, entry in enumerate(self.data['entries']):
            observed = set()
            distinct = set()
            stat_values = [set() for _ in range(6)]
            allowed = {m['native_id']: m['native_pp'] for m in entry['npc_move_pool']}
            self.assertEqual(len(allowed), 20)
            self.assertEqual(sum(m['category'] == 'status' for m in entry['npc_move_pool']), 6)
            base = [entry['base_stats'][k] for k in self.data['stat_order']]
            for seed in range(2048):
                result = self.sample(profile, seed)
                moves = tuple(result.moves)
                self.assertEqual(len(set(moves)), 4)
                self.assertTrue(set(moves) <= allowed.keys())
                categories = {m['native_id']: m['category'] for m in entry['npc_move_pool']}
                self.assertGreaterEqual(sum(categories[m] != 'status' for m in moves), self.data['policy']['minimum_offensive_moves'])
                self.assertEqual(list(result.pp), [allowed[m] for m in moves])
                self.assertTrue(all(24 <= iv <= 31 for iv in result.ivs))
                self.assertEqual(sum(result.evs), 508)
                self.assertTrue(all(ev <= 252 and ev % 4 == 0 for ev in result.evs))
                self.assertEqual(list(result.stats), expected_stats(base, result.ivs, result.evs, result.nature, 50))
                for index, stat in enumerate(result.stats):
                    stat_values[index].add(stat)
                observed.update(moves)
                distinct.add(tuple(sorted(moves)))
            self.assertEqual(observed, set(allowed))
            self.assertGreater(len(distinct), 500)
            self.assertTrue(all(len(values) > 1 for values in stat_values))

    def test_optional_free_draw_can_pick_four_status_but_default_rejects_it(self):
        free = copy.deepcopy(self.data)
        free['policy']['minimum_offensive_moves'] = 0
        folder = self.folder / 'free'
        folder.mkdir()
        (folder / 'battle_rules.h').write_text(header(free))
        path = folder / ('free.dll' if sys.platform == 'win32' else 'free.so')
        subprocess.run([shutil.which('gcc'), '-O2', '-shared', '-fPIC', '-I', str(folder),
                        str(ROOT / 'content/tools/random_sets.c'), '-o', str(path)], check=True)
        library = ctypes.CDLL(str(path))
        library.shared_generate.argtypes = self.lib.shared_generate.argtypes
        categories = {m['native_id']: m['category'] for m in self.data['entries'][0]['npc_move_pool']}
        for seed in range(8192):
            result = SharedSet()
            self.assertEqual(library.shared_generate(0, seed, 50, ctypes.byref(result)), 1)
            if all(categories[m] == 'status' for m in result.moves):
                guarded = self.sample(0, seed)
                self.assertTrue(any(categories[m] != 'status' for m in guarded.moves))
                return
        self.fail('No all-status case exercised')

    def test_seed_is_repeatable_and_level_uses_native_formula(self):
        for profile, entry in enumerate(self.data['entries']):
            for seed in (0, 1, 42, 0xffffffff):
                a = self.sample(profile, seed)
                b = self.sample(profile, seed)
                self.assertEqual(bytes(a), bytes(b))
                for level in (5, 50, 100):
                    result = self.sample(profile, seed, level)
                    base = [entry['base_stats'][k] for k in self.data['stat_order']]
                    self.assertEqual(list(result.stats), expected_stats(base, result.ivs, result.evs, result.nature, level))

    def test_bad_arguments_do_not_modify_output(self):
        for profile, level in ((99, 50), (0, 0), (0, 101)):
            result = SharedSet()
            ctypes.memset(ctypes.byref(result), 0x5a, ctypes.sizeof(result))
            before = bytes(result)
            self.assertEqual(self.lib.shared_generate(profile, 1, level, ctypes.byref(result)), 0)
            self.assertEqual(bytes(result), before)

    def test_native_replay_proof_matches_compiled_inputs(self):
        proof = json.loads((ROOT / 'content/pokemon/native-randomizer-proof.json').read_text())
        self.assertEqual(proof['source_sha256'], hashlib.sha256((ROOT / 'content/tools/random_sets.c').read_bytes()).hexdigest())
        self.assertEqual(proof['compiled_rules_header_sha256'], hashlib.sha256(header(self.data).encode()).hexdigest())
        self.assertTrue(proof['passed'])
        self.assertFalse(proof['npc_generation_hook_installed'])

    def test_pass_keeps_snivy_and_mega_lucario_and_fixed_player_set(self):
        entries = self.data['entries']
        replacements = [e for e in entries if e['rental_pass'].get('action') != 'preserve_existing']
        self.assertEqual([e['rental_pass']['slot'] for e in replacements], [2, 3, 4, 5])
        presets = {e['key']: e for e in entries}
        self.assertEqual(presets['snivy']['player_moves'], [412, 137, 73, 182])
        self.assertEqual(presets['mega-lucario']['player_moves'], [418, 370, 396, 182])
        self.assertEqual(presets['snivy']['rental_pass']['action'], 'preserve_existing')
        self.assertEqual(presets['mega-lucario']['rental_pass']['action'], 'preserve_existing')
        self.assertTrue(all(e['rental_pass']['preserve_slots'] == [0, 1] for e in entries))
        self.assertEqual(entries[0]['player_moves'], [394, 337, 89, 182])
        self.assertFalse(self.data['policy']['player_presets_randomized'])


if __name__ == '__main__':
    unittest.main()
