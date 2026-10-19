import json,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from benchmarks.player_match_groups.closed_full_tree_fixture import case,run
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.actor_information import PersonalInformation


class ValueLawCacheTests(unittest.TestCase):
    def source(self):
        c=ClosedCalculation(case(6,'dual').data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30);node=c.root
        for target in (3,6):node=node.observe(target)[1]
        return c,node

    def test_exact_repeated_input_reuses_only_existing_common_transformation(self):
        import werewolf.information_set_forecast as info
        c,node=self.source();e=c._ClosedCalculation__engine;s=node.read().private
        before=s;expected=InformationSetForecast.value_law(e,s)
        with patch.object(info,'normalize',wraps=info.normalize) as normalization:
            first=e.value_law(s);second=e.value_law(replace(s))
            self.assertEqual(first,expected);self.assertIs(first,second);self.assertEqual(normalization.call_count,1)
        self.assertEqual(s,before);self.assertTrue(any(h.attacks for h in s.hypotheses))
        self.assertTrue(all(not h.attacks for h in first.hypotheses))
        self.assertEqual(first.public_roles,s.public_roles)
        self.assertEqual((first.rosters,first.tracked,first.observed_prefix),(s.rosters,s.tracked,s.observed_prefix))

    def test_configuration_and_metadata_are_not_mixed(self):
        c,node=self.source();e=c._ClosedCalculation__engine;s=node.read().private
        normalized=e.value_law(s);old_rules=e.rules;old_strategy=e.strategy
        e.rules=replace(old_rules,allow_repeat_guard=False);self.assertIs(e.value_law(s),s)
        e.rules=old_rules;e.strategy=replace(old_strategy,night='max');self.assertIs(e.value_law(s),s)
        e.strategy=old_strategy;self.assertIs(e.value_law(s),normalized)
        different=replace(s,observed_prefix=0 if s.observed_prefix else 1);self.assertNotEqual(e.value_law(different),normalized)
        self.assertEqual(e.value_law(different),InformationSetForecast.value_law(e,different))

    def test_cache_is_calculation_local_and_conditioning_keeps_whole_law(self):
        c,node=self.source();e=c._ClosedCalculation__engine;full=e.value_law(node.read().private)
        h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
        _,owner=node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))
        own=e.value_law(owner.read().private)
        self.assertNotEqual(own,full);self.assertEqual(own,InformationSetForecast.value_law(e,owner.read().private))
        other,second=self.source();f=other._ClosedCalculation__engine
        self.assertEqual(f.value_laws,{})
        self.assertIsNot(f.value_law(second.read().private),full);self.assertEqual(f.value_law(second.read().private),full)

    def test_same_role_marginal_different_scan_history_cannot_share_input(self):
        c=ClosedCalculation(case(6,'single').data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)
        node=next(r.node for r in c.root.action(2) if r.node.read().public.winner is None)
        node=next(r.node for r in node.action(6) if r.node.read().public.winner is None)
        rows={r.node.read().past[-1].target:r.node for r in node.reports() if r.node.read().past[-1].color=='white'}
        a,b=rows[2],rows[6];e=c._ClosedCalculation__engine
        self.assertEqual(a.read().public.worlds,b.read().public.worlds)
        self.assertNotEqual(e.value_law(a.read().private),e.value_law(b.read().private))
        from werewolf.seer_future_uniform import candidates
        pa={candidates(h,1,a.read().private.rosters[0]) for h in a.read().private.hypotheses}
        pb={candidates(h,1,b.read().private.rosters[0]) for h in b.read().private.hypotheses}
        self.assertEqual(pa,{(4,5,6)});self.assertEqual(pb,{(2,4,5)})

    def test_complete_forecast_tables_and_independent_cold_for_public_and_owners(self):
        results=[]
        for view in ('public','seer','wolf'):
            r=run(6,'dual',view,'forecast');self.assertEqual(r['returncode'],0,r);self.assertIsNone(r['termination'])
            self.assertEqual(r['worker']['status'],'verified',r)
            self.assertTrue(r['worker']['forecasts'][0]['expanded_cold_Forecast_Table_equal'])
            self.assertEqual(r['worker']['forecasts'][0]['village_win'],'3/8');results.append(r)
        Path('benchmarks/player_match_groups/value-law-cache-small-validation.json').write_text(json.dumps(dict(status='verified',cases=results),indent=2)+'\n',encoding='utf-8')
