import unittest
from unittest.mock import patch
from dataclasses import replace
from benchmarks.player_match_groups.extension_cases import fixture,prepare_game
from benchmarks.player_match_groups.extension_reuse import ExtensionForecast
from benchmarks.player_match_groups.measure_future_reuse import run
from benchmarks.player_match_groups.history_validation import run as history_run
from werewolf.exact_renaming import canonical_key


class ExtensionReuseTests(unittest.TestCase):
    def test_complete_small_medium_and_max_tables(self):
        for config,options in (({'mediums':1},{'medium_reuse':True}),({'day':'max'},{'max_reuse':True}),({'night':'max'},{'max_reuse':True}),({'day':'max','night':'max','fake':'max'},{'max_reuse':True})):
            _,game=fixture(**config);prepared=prepare_game(game)
            old=run(prepared=prepared,max_seconds=10)
            new=run(enabled=True,physical_reuse=True,compact_keys=True,fast_parts=True,prepared=prepared,engine_class=ExtensionForecast,engine_options=options,max_seconds=10)
            self.assertTrue(old['complete']);self.assertTrue(new['complete'])
            self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
            self.assertGreater(new['stats']['key_value_hits'],0)
            self.assertLess(new['expansions']['actions'],old['expansions']['actions'])

    def test_separate_guards_and_full_configuration(self):
        _,game=fixture(mediums=1);_,_,b,s,past,rules,strategy,_=prepare_game(game)
        e=ExtensionForecast(rules,strategy,future_reuse=True,medium_reuse=True)
        key=e.full_renamed_key(b,s,past,s,None,physical=b)
        self.assertEqual(key,canonical_key(b,s,past,s,None,rules,strategy,physical=b,max_mappings=120))
        self.assertGreater(e.reuse_stats['key_requests'],0)
        e.strategy=replace(strategy,day='max')
        before=e.reuse_stats['key_requests'];e.full_renamed_key(b,s,past,s,None,physical=b)
        self.assertEqual(e.reuse_stats['key_requests'],before)
        # Neither flag enables the medium+max combination.
        e.max_reuse=True;e.full_renamed_key(b,s,past,s,None,physical=b)
        self.assertEqual(e.reuse_stats['key_requests'],before)
        e.strategy=strategy;e.reuse_public_entry=False
        e.full_renamed_key(b,s,past,s,None,physical=b)
        self.assertEqual(e.reuse_stats['key_requests'],before)

    def test_correction_withdrawal_death_and_view_switch(self):
        result=history_run()
        self.assertTrue(all(row['equal']for row in result['stages']))
        self.assertTrue(result['private_matches_original'])
        self.assertTrue(result['public_private_public_stable'])
        root=[row for row in result['stages']if row['new']['kind']=='root']
        self.assertTrue(root)
        self.assertTrue(all(row['new']['engines']==0 for row in root))

    def test_complete_labelled_max_vectors_and_actor_ties(self):
        from benchmarks.player_match_groups.policy_vector_validation import run as vectors
        for mediums,retirement in ((0,False),(1,False),(1,True)):
            result=vectors(mediums,retirement)
            self.assertTrue(result['exact_vectors_and_ties_equal'])
            self.assertGreater(result['night_actor_vectors'],0)

    def test_hunter_remains_on_existing_route(self):
        from werewolf.exact import initial_board
        from werewolf.seer_acquisition import from_board
        from werewolf.seer_future_uniform import TrueScanState
        _,game=fixture(day='max');_,_,_,_,past,rules,strategy,_=prepare_game(game)
        b=initial_board(5,1,0,1,1,experimental_cast=True)
        s=TrueScanState(from_board(b),(tuple(b.alive),),'none',())
        e=ExtensionForecast(rules,strategy,future_reuse=True,medium_reuse=True,max_reuse=True,combined_reuse=True,retirement_proof=True)
        e.full_renamed_key(b,s,(),s,None,physical=b)
        self.assertEqual(e.reuse_stats['key_requests'],0)
        self.assertEqual(e.retirement_proof_hits,0)

    def test_noise_preserves_each_wolf_information_law(self):
        from benchmarks.player_match_groups.retirement_probe import probe
        self.assertEqual(probe(6,2)['rows'],[])
        result=probe(6,2,expose_truth=True)
        self.assertTrue(result['rows'])
        for row in result['rows']:
            self.assertGreater(row['wolf_information_groups'],1)
            self.assertTrue(row['private_conditional_laws_unchanged'])
            self.assertTrue(row['all_role_posteriors_unchanged'])

    def test_extended_retirement_complete_medium_max(self):
        _,game=fixture(n=6,wolves=2,mediums=1,day='max',night='max',fake='max')
        prepared=prepare_game(game)
        old=run(prepared=prepared,max_seconds=10)
        new=run(enabled=True,physical_reuse=True,retired_reuse=True,compact_keys=True,fast_parts=True,retirement_proof=True,prepared=prepared,engine_class=ExtensionForecast,engine_options={'combined_reuse':True,'extended_retirement':True},max_seconds=10)
        self.assertTrue(old['complete']);self.assertTrue(new['complete'])
        self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
        self.assertGreater(new['retirement_proof_hits'],0)

    def test_medium_max_private_switch_never_retains_other_secrets(self):
        from werewolf.information_set_forecast import InformationSetForecast
        from werewolf.calculation_budget import calculation_budget
        _,game=fixture(mediums=1,day='max',night='max',fake='max')
        _,_,b,s,past,rules,strategy,_=prepare_game(game)
        e=ExtensionForecast(rules,strategy,future_reuse=True,combined_reuse=True,extended_retirement=True,retirement_proof=True,physical_reuse=True)
        with calculation_budget(1000000,max_seconds=10):
            public=e.scalar(b,s,past);hits=e.retirement_proof_hits
            private=e.evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
            expected=InformationSetForecast(rules,strategy).evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
            self.assertEqual(private,expected);self.assertEqual(e.retirement_proof_hits,hits)
            self.assertEqual(e.scalar(b,s,past),public)

    def test_own_seer_observer_stays_on_original_private_path(self):
        from werewolf.seer_view_forecast import seer_forecast
        from werewolf.seer_future_uniform import FuturePending
        _,game=fixture(mediums=1,day='max',night='max',fake='max')
        _,_,b,s,past,rules,strategy,_=prepare_game(game)
        h=next(h for h in s.hypotheses if h.roles[2]&1)
        own=tuple(a for a in h.acquisitions if a.player==1)
        original=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=10)
        engines=[]
        def factory(*args,**kwargs):
            e=ExtensionForecast(*args,future_reuse=True,physical_reuse=True,combined_reuse=True,extended_retirement=True,retirement_proof=True,**kwargs);engines.append(e);return e
        with patch('werewolf.seer_view_forecast.InformationSetForecast',factory):
            trial=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=10)
        self.assertNotIsInstance(original,FuturePending)
        self.assertTrue(all(v==1 for _,v in original))
        self.assertEqual(original,trial)
        self.assertTrue(engines)
        self.assertTrue(all(e.reuse_stats['key_requests']==e.retirement_proof_hits==0 for e in engines))

    def test_supported_own_seer_observer_exact_values(self):
        from tests.test_seer_view_forecast import fixture as private_fixture
        from werewolf.seer_view_forecast import seer_forecast
        from werewolf.seer_future_uniform import FuturePending
        from werewolf.exact import Rules,Strategy
        b,s=private_fixture();rules=Rules(initial_seer='none');strategy=Strategy('max','random')
        original=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=10)
        engines=[]
        def factory(*args,**kwargs):
            e=ExtensionForecast(*args,future_reuse=True,physical_reuse=True,max_reuse=True,extended_retirement=True,retirement_proof=True,**kwargs);engines.append(e);return e
        with patch('werewolf.seer_view_forecast.InformationSetForecast',factory):
            trial=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=10)
        self.assertNotIsInstance(original,FuturePending);self.assertEqual(original,trial)
        self.assertTrue(all(e.reuse_stats['key_requests']==e.retirement_proof_hits==0 for e in engines))
