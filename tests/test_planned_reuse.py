import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.extension_cases import fixture,prepare_game
from benchmarks.player_match_groups.planned_reuse import PlannedReuseForecast
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.model_a_public import public_forecast
from werewolf.seer_view_forecast import seer_forecast

class PlannedReuseTests(unittest.TestCase):
    def test_cold_and_warm_complete_public_and_owner_arrays_match(self):
        _,g=fixture();_,_,b,s,past,rules,strategy,_=prepare_game(g);reference=None
        for cls in(InformationSetForecast,PlannedReuseForecast):
            e=cls(rules,strategy,**({}if cls is InformationSetForecast else dict(future_reuse=True,compact_keys=True,fast_parts=True)))
            for warmth in range(2):
                with patch('werewolf.local_reuse.make_public_engine',lambda *a,**kw:e),patch('werewolf.local_reuse.make_view_engine',lambda *a,**kw:e):
                    forecast=public_forecast(b,s,past,rules,strategy,max_seconds=8)
                    own=next(h.acquisitions for h in s.hypotheses if h.roles[2]&1)
                    seer=seer_forecast(b,1,own,rules,strategy,scan_state=s,past=past,max_seconds=8)
                    wolf=e.evaluate(b,s,past,mask=s.hypotheses[0].roles[0])
                self.assertIsInstance(seer,tuple)
                output=forecast,seer,wolf,tuple((t,e.public_children(b,t,s),e.physical_children(b,t))for t in b.alive)
                if reference is None:reference=output
                self.assertEqual(output,reference)
            if cls is PlannedReuseForecast:self.assertGreater(e.plan_stats['complete'],0)
    def test_over_cap_selector_keeps_current_keys_and_only_proves_missing_case(self):
        from tests.test_bounded_key_plan import BoundedKeyPlanTests
        from benchmarks.player_match_groups.planned_reuse import OverCapReuseForecast
        from werewolf.exact_renaming import canonical_key
        b,s,rules,strategy=BoundedKeyPlanTests().fixture()
        e=OverCapReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True)
        target=e.full_renamed_key(b,s,(),s,None,target=1)
        self.assertIsNotNone(target);self.assertEqual(e.plan_stats['calls'],0)
        scalar=e.full_renamed_key(b,s,(),s,None)
        self.assertIsNotNone(scalar);self.assertEqual(e.plan_stats['over_cap_completed'],1)
        expected=canonical_key(b,s,(),s,None,rules,strategy,max_mappings=1000)
        self.assertEqual(getattr(scalar,'values',scalar),expected)
        self.assertIsNone(e.full_renamed_key(b,s,(),s,lambda h,s:True))
        self.assertEqual(e.plan_stats['calls'],1)

    def test_over_cap_selector_does_not_ignore_cyclic_private_correlations(self):
        from tests.test_bounded_key_plan import BoundedKeyPlanTests
        from benchmarks.player_match_groups.planned_reuse import OverCapReuseForecast
        from dataclasses import replace
        from fractions import Fraction as F
        from werewolf.night_knowledge import WolfAttack
        from werewolf.seer_acquisition import normalize
        b,s,rules,strategy=BoundedKeyPlanTests().fixture()
        hs=normalize(tuple(replace(h,attacks=(WolfAttack(1,t),),mass=F(1,30))for h in s.hypotheses for t in b.alive if not h.roles[0]&(1<<(t-1))))
        public=replace(s,hypotheses=hs,rosters=(b.alive,b.alive))
        private=replace(public,hypotheses=normalize(tuple(h for h in hs if h.attacks[0].target==(h.roles[0].bit_length()%6)+1)))
        e=OverCapReuseForecast(rules,strategy,future_reuse=True,compact_keys=True,fast_parts=True)
        self.assertIsNone(e.full_renamed_key(b,public,(),private,None))
        self.assertEqual(e.plan_stats['residual_mapping_limit'],1)