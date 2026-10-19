import unittest
from fractions import Fraction as F
from dataclasses import replace
from unittest.mock import patch
from threading import Event
from time import monotonic
from tests.test_terminal_max_report import make,ordinary
from benchmarks.player_match_groups.report_integral_design import oracle
from benchmarks.player_match_groups.dead_history_design import terminal_public_payoff_moments
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import tables
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.morning_publications import compile_publications,PublicMomentCache
from werewolf.information_set_forecast import Pending
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded,tick


def incomplete():return Pending('information_set_report_likelihood_incomplete')


def zero_frame():
    from werewolf.exact import initial_board,replace_worlds
    from werewolf.seer_acquisition import from_board
    from werewolf.seer_future_uniform import TrueScanState
    b=replace_worlds(initial_board(3,1,0),((1,0,0,0,F(2,3)),(2,0,0,0,F(1,3))),day=2)
    s=TrueScanState(from_board(b),((1,2,3),(1,2,3)),initial_rule='none',tracked=())
    return b,s


class PublicMomentCacheTests(unittest.TestCase):
    def test_private_order_uncached_and_independent_joint_enumeration(self):
        for kind,target in (('single',3),('dual',3),('three',4)):
            c,n=make(kind,target);e=c._ClosedCalculation__engine;s=n.read()
            h=next(h for h in s.private.hypotheses if h.roles[2]&1)
            nodes=(n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(WolfInformation.from_hypothesis(h))[1])
            with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                kernel=e.publication_kernel(s.public,s.public_state,s.past)
                for order in ((0,1,2),(2,1,0),(1,2,0)):
                    cache=PublicMomentCache();seen={}
                    for i in order:
                        source=nodes[i].read();events,_=oracle(source)
                        expected_moments,qpi=terminal_public_payoff_moments(source,events)
                        expected=sum((h.mass*expected_moments.get((h.roles,h.acquisitions),F())/qpi[h.roles,h.acquisitions] for h in source.private.hypotheses),F())
                        cold=kernel.terminal_execution_value(source.private,s.public.alive,incomplete=incomplete)
                        if seen:
                            with patch.object(kernel,'terminal_execution_moments',side_effect=AssertionError('P caused rebuild')):
                                actual=kernel.terminal_execution_value(source.private,s.public.alive,incomplete=incomplete,cache=cache)
                        else:actual=kernel.terminal_execution_value(source.private,s.public.alive,incomplete=incomplete,cache=cache)
                        self.assertEqual(actual,cold);self.assertEqual(actual,expected);seen[i]=actual
                    self.assertEqual(len(cache.entries),1)
                    self.assertEqual(dict(next(iter(cache.entries.values()))),expected_moments)

    def test_complete_forecast_tables_reports_cold_and_cache_disabled(self):
        for kind,target in (('dual',3),('three',4),('medium-pair',4)):
            c,n=make(kind,target);e=c._ClosedCalculation__engine
            expected,old=ordinary(n.read(),e.rules)
            actual=n.forecast();self.assertEqual(actual,expected)
            self.assertEqual(tables(n.read(),actual),tables(n.read(),expected))
            e.terminal_moments=None;e.values.clear();e.action_values.clear()
            self.assertEqual(n.forecast(),actual)
            cold=n.export_request().roles();self.assertEqual(cold,n.read())
            with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports()),old.report_children(cold))

    def test_different_public_sources_histories_named_targets_and_calculations_do_not_collide(self):
        c,n=make('three',4);e=c._ClosedCalculation__engine;s=n.read();cache=PublicMomentCache()
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            k=e.publication_kernel(s.public,s.public_state,s.past)
            original=k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)
            forced=k.terminal_execution_value(s.private,(s.public.alive[0],),incomplete=incomplete,cache=cache)
            self.assertNotEqual(original,forced)
            children=e.report_children(s);child=next(row[2] for row in children if old_value(row[2],e.rules)!=original)
            k2=e.publication_kernel(child.public,child.public_state,child.past)
            self.assertIsNot(k,k2)
            got=k2.terminal_execution_value(child.private,child.public.alive,incomplete=incomplete,cache=cache)
            self.assertEqual(got,old_value(child,e.rules));self.assertNotEqual(got,original)
            # A cold equivalent input must not find another calculation's entry.
            cold=n.export_request().roles();c2,n2=make('three',4);e2=c2._ClosedCalculation__engine
            k3=e2.publication_kernel(cold.public,cold.public_state,cold.past)
            with patch.object(k3,'terminal_execution_moments',wraps=k3.terminal_execution_moments) as build:
                self.assertEqual(k3.terminal_execution_value(cold.private,cold.public.alive,incomplete=incomplete,cache=cache),original)
                self.assertEqual(build.call_count,1)
            self.assertIsNot(e.terminal_moments,e2.terminal_moments)
            self.assertEqual(len(e2.terminal_moments.entries),0)
            self.assertEqual(len(cache.entries),4)

    def test_configured_fake_policy_is_owned_by_each_public_kernel(self):
        c,n=make('three',4);source=n.read();cache=PublicMomentCache();values=[]
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            for policy,plausible in ((('noncontradictory','uniform'),True),(('uniform',),False)):
                k=compile_publications(source.public_state,source.past,source.public.alive,source.public.claims,board=source.public,fake_policy=policy)
                events,unused=oracle(source,plausible=plausible)
                moments,qpi=terminal_public_payoff_moments(source,events)
                expected=sum((h.mass*moments.get((h.roles,h.acquisitions),F())/qpi[h.roles,h.acquisitions] for h in source.private.hypotheses),F())
                actual=k.terminal_execution_value(source.private,source.public.alive,incomplete=incomplete,cache=cache)
                self.assertEqual(actual,expected);values.append(actual)
            self.assertNotEqual(*values)
            self.assertEqual(len(cache.entries),2)

    def test_same_public_scalar_different_Q_weights_do_not_share_private_values(self):
        from werewolf.exact import replace_worlds
        b,s=zero_frame()
        q2=replace(s,hypotheses=tuple(replace(h,mass=F(1)-h.mass) for h in s.hypotheses))
        b2=replace_worlds(b,q2.public_roles)
        p=replace(s,hypotheses=(replace(s.hypotheses[0],mass=F(1)),))
        k1=compile_publications(s,(),b.alive,b.claims,board=b)
        k2=compile_publications(q2,(),b2.alive,b2.claims,board=b2);cache=PublicMomentCache()
        with calculation_budget(250000,max_seconds=30):
            self.assertEqual(k1.terminal_execution_value(s,b.alive,incomplete=incomplete,cache=cache),F(2,3))
            self.assertEqual(k2.terminal_execution_value(q2,b.alive,incomplete=incomplete,cache=cache),F(2,3))
            self.assertEqual(k1.terminal_execution_value(p,b.alive,incomplete=incomplete,cache=cache),1)
            self.assertEqual(k2.terminal_execution_value(p,b.alive,incomplete=incomplete,cache=cache),0)
            self.assertEqual(len(cache.entries),2)

    def test_initial_full_private_forecasts_match_in_reversed_view_order(self):
        for order in ((0,1,2),(2,1,0)):
            c,n=make('dual',3);root=c.root;e=c._ClosedCalculation__engine
            h=next(h for h in root.read().private.hypotheses if h.roles[2]&1)
            nodes=(root,root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],root.personal(WolfInformation.from_hypothesis(h))[1])
            for i in order:
                source=nodes[i].read();expected,unused=ordinary(source,e.rules)
                actual=nodes[i].forecast();self.assertEqual(actual,expected)
                self.assertEqual(tables(source,actual),tables(source,expected))
                self.assertEqual(nodes[i].export_request().roles(),source)
            self.assertLessEqual(len(e.terminal_moments.entries),128)
            self.assertLessEqual(e.terminal_moments.rows,4096)

    def test_zero_payoff_is_supported_and_unknown_private_input_still_refuses_on_hit(self):
        b,s=zero_frame();k=compile_publications(s,(),b.alive,b.claims,board=b);cache=PublicMomentCache()
        p=replace(s,hypotheses=(replace(s.hypotheses[1],mass=F(1)),))
        with calculation_budget(250000,max_seconds=30):
            self.assertEqual(k.terminal_execution_value(s,b.alive,incomplete=incomplete,cache=cache),F(2,3))
            self.assertEqual(k.terminal_execution_value(p,b.alive,incomplete=incomplete,cache=cache),0)
            self.assertIn(F(),dict(next(iter(cache.entries.values()))).values())
            bad=replace(p,hypotheses=(replace(p.hypotheses[0],roles=(4,0,0,0)),))
            with self.assertRaises(Pending):k.terminal_execution_value(bad,b.alive,incomplete=incomplete,cache=cache)

    def test_capacity_eviction_and_oversized_uncached_values_are_exact(self):
        b,s=zero_frame();k=compile_publications(s,(),b.alive,b.claims,board=b)
        tiny=PublicMomentCache(max_entries=1,max_rows=1)
        with calculation_budget(250000,max_seconds=30):
            for unused in range(2):self.assertEqual(k.terminal_execution_value(s,b.alive,incomplete=incomplete,cache=tiny),F(2,3))
            self.assertEqual(tiny.rows,0);self.assertFalse(tiny.entries)
            bounded=PublicMomentCache(max_entries=1,max_rows=2)
            k.terminal_execution_value(s,b.alive,incomplete=incomplete,cache=bounded)
            k.terminal_execution_value(s,(2,),incomplete=incomplete,cache=bounded)
            self.assertEqual(len(bounded.entries),1);self.assertEqual(bounded.rows,2)
            self.assertEqual(k.terminal_execution_value(s,b.alive,incomplete=incomplete,cache=bounded),F(2,3))
            self.assertEqual(len(bounded.entries),1);self.assertLessEqual(bounded.rows,2)

    def test_partial_build_is_not_cached_and_warm_hits_poll_resource_stops(self):
        c,n=make('three',4);e=c._ClosedCalculation__engine;s=n.read();cache=PublicMomentCache()
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):k=e.publication_kernel(s.public,s.public_state,s.past)
        with calculation_budget(1,max_seconds=30),self.assertRaises(CalculationBudgetExceeded):
            k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)
        self.assertFalse(cache.entries)
        with calculation_budget(250000,max_seconds=30):k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)
        stop=Event();stop.set()
        with cancellation_scope(stop),self.assertRaises(CalculationCancelled):k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)
        with calculation_budget(1,max_seconds=30):
            with self.assertRaises(CalculationBudgetExceeded):tick(2)
            with self.assertRaises(CalculationBudgetExceeded):k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)
        with calculation_budget(100,max_seconds=1),patch('werewolf.calculation_budget.monotonic',return_value=monotonic()+100),self.assertRaises(CalculationBudgetExceeded):
            k.terminal_execution_value(s.private,s.public.alive,incomplete=incomplete,cache=cache)


def old_value(source,rules):
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.exact import Strategy
    return InformationSetForecast(rules,Strategy(),retire_uninformative_scans=False,exact_renaming=False).action_policy.morning_value(source)

if __name__=='__main__':unittest.main()
