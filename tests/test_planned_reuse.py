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