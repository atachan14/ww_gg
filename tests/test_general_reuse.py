import unittest,copy,json
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.extension_cases import fixture,prepare_game,game_of
from benchmarks.player_match_groups.measure_future_reuse import run
from benchmarks.player_match_groups.original_reference import OriginalForecastAdapter
from benchmarks.player_match_groups.general_reuse import GeneralReuseForecast
from werewolf.exact_renaming import canonical_key
from werewolf.seer_intervention import SeerObserver
from werewolf.seer_view_forecast import seer_forecast
from werewolf.local_reuse import reuse_scope
from werewolf.seer_future_uniform import FuturePending

class GeneralReuseTests(unittest.TestCase):
    def test_different_reports_and_nonuniform_full_laws(self):
        c,g=fixture()
        payload={'claims':g['claims'],'seers':[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':1,'reporter':2,'target':4,'color':'white'}],'mediums':[]}
        self.assertEqual(c.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)}).status_code,200)
        prepared=prepare_game(game_of(c))
        for medium in(False,True):
            p=prepare_game(fixture(mediums=1)[1])if medium else prepared
            old=run(prepared=p,engine_class=OriginalForecastAdapter,max_seconds=15)
            new=run(prepared=p,engine_class=GeneralReuseForecast,enabled=True,compact_keys=True,fast_parts=True,max_seconds=15)
            self.assertTrue(old['complete']);self.assertTrue(new['complete'])
            self.assertEqual((old['value'],old['table']),(new['value'],new['table']))
            self.assertGreater(new['stats']['key_supported'],0)

    def test_personal_observer_full_history_and_target_identity(self):
        _,_,b,s,past,rules,strategy,_=prepare_game(fixture()[1])
        h=next(h for h in s.hypotheses if h.roles[2]&1)
        own=tuple(a for a in h.acquisitions if a.player==1)
        observer=SeerObserver(1,own,2,4)
        key=canonical_key(b,s,past,s,observer,rules,strategy)
        self.assertIsNotNone(key)
        self.assertNotEqual(key,canonical_key(b,s,past,s,replace(observer,target=3),rules,strategy))
        self.assertIsNone(canonical_key(b,s,past,s,lambda h,s:True,rules,strategy))
        with reuse_scope(False):old=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=15)
        made=[]
        def factory(*a,**kw):
            e=GeneralReuseForecast(*a,future_reuse=True,compact_keys=True,fast_parts=True,**kw);made.append(e);return e
        with reuse_scope(True),patch('werewolf.local_reuse.make_view_engine',lambda original,public,*a,**kw:factory(*a,**kw)):
            new=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=15)
        self.assertNotIsInstance(old,FuturePending);self.assertEqual(old,new)
        self.assertGreater(made[0].reuse_stats['key_supported'],0)
        self.assertEqual(made[0].retirement_proof_hits,0)

    def test_hunter_gj_keys_keep_all_private_records(self):
        import tests.test_guard_no_repeat as cases
        from werewolf.seer_manual import replay
        from werewolf.exact import Strategy
        from werewolf.root_secret_flow import prepare_root_entry
        for repeat in(False,True):
            g=cases.NoRepeatGuardTests().fixture(repeat=repeat)
            rules,p=replay(g);strategy=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,rules,strategy)
            b,s=root.public,root.public_law
            e=GeneralReuseForecast(rules,strategy,future_reuse=True,fast_parts=True)
            key=e.full_renamed_key(b,s,root.past,root.physical_law,None,physical=root.physical)
            self.assertEqual(key,canonical_key(b,s,root.past,root.physical_law,None,rules,strategy,physical=root.physical,max_mappings=120))
            self.assertIsNotNone(key)
            changed=replace(root.physical_law,hypotheses=tuple(replace(h,attacks=())for h in root.physical_law.hypotheses))
            self.assertNotEqual(key,e.full_renamed_key(b,s,root.past,changed,None,physical=root.physical))
            self.assertFalse(e.retirement_proof)

    def test_nonuniform_history_private_actions_match(self):
        from tests.test_seer_view_forecast import fixture as weighted
        from werewolf.exact import Rules,Strategy
        b,s=weighted();rules=Rules(initial_seer='none');strategy=Strategy('max','random')
        with reuse_scope(False):old=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=15)
        with reuse_scope(True):new=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=15)
        self.assertEqual(old,new)
        self.assertEqual(dict(new)[5],F(7,10))

    def test_new_key_cap_preserves_existing_legacy_constructor(self):
        from werewolf.information_set_forecast import InformationSetForecast
        _,_,b,s,past,rules,strategy,_=prepare_game(fixture()[1])
        e=GeneralReuseForecast(rules,strategy,future_reuse=True)
        with patch.object(e,'complete_reuse_key',return_value=None),patch.object(InformationSetForecast,'full_renamed_key',return_value='legacy-constructor'):
            self.assertEqual(e.full_renamed_key(b,s,past,s,None),'legacy-constructor')
