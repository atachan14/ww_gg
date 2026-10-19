import unittest
from dataclasses import asdict,replace
from fractions import Fraction as F
from threading import Event
from benchmarks.player_match_groups.payoff_vector_experiment import PayoffVectorExperiment
from benchmarks.player_match_groups.payoff_vector_probe import nodes
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from benchmarks.player_match_groups.exposed_fake_channel import named_reference
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from werewolf.closed_calculation import ClosedCalculation
from werewolf.exact import Strategy
from werewolf.board_future import kernel_calculation
from werewolf.evaluation_branch import physical_board
from werewolf.seer_intervention import SeerObserver
from werewolf.information_set_forecast import Pending
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled,CalculationBudgetExceeded


def make(kind):return ClosedCalculation(case(5,kind).data.updated(policy=asdict(Strategy())),grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)


class PayoffVectorTests(unittest.TestCase):
    def test_full_nonterminal_public_multiple_owner_Forecast_Table_and_cold(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            for kind in ('dual','three'):
                c=make(kind);v=PayoffVectorExperiment(c);selected=nodes(c,True)
                before=tuple(n.read() for n in selected);self.assertEqual(len(c.root.read().public.alive),5)
                for node in selected:
                    s=node.read();ref=named_reference(c._ClosedCalculation__engine,s);want=forecast(ref,s);got=v.forecast(node)
                    self.assertEqual(got,want);self.assertEqual(tables(s,got),tables(s,want))
                    self.assertEqual(node.read(),s);self.assertEqual(node.export_request().roles(),s)
                self.assertEqual(tuple(n.read() for n in selected),before)
                self.assertGreater(v.stats()['physical_branches'],0)
                self.assertGreater(v.stats()['terminal_moment_applications'],0)
                # Additional viewers reuse the completed operator, not a new
                # actual-P physical tree. Q policy selection stays common.
                counts=(len(v.values),len(v.actions))
                for node in reversed(selected):self.assertEqual(v.forecast(node),forecast(named_reference(c._ClosedCalculation__engine,node.read()),node.read()))
                self.assertEqual(counts,(len(v.values),len(v.actions)))

    def test_each_root_secret_and_nonuniform_P_match_independent_exact_scalar(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c=make('dual');v=PayoffVectorExperiment(c);s=c.root.read();v.forecast(c.root)
            masses=((F(1),F()),(F(),F(1)),(F(1,4),F(3,4)))
            for weights in masses:
                p=replace(s.private,hypotheses=tuple(replace(h,mass=q) for h,q in zip(s.private.hypotheses,weights) if q))
                own=replace(s,private=p,physical=physical_board(s.public,p,s.physical))
                want=forecast(named_reference(c._ClosedCalculation__engine,own),own)
                self.assertEqual(v.apply(v.solve(v.root),p),want.village_win)
                self.assertEqual(tuple((t,v.apply(v.act(v.root,t),p)) for t,value in want.action_values),want.action_values)
            joint=v.solve(v.root)
            self.assertTrue(all(0<=x/q<=1 for x,q in zip(joint,v.prior)))

    def test_named_report_history_unchanged_after_vector_build(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c=make('three');v=PayoffVectorExperiment(c);n=c.root
            for target in (4,5):n=next(row.node for row in n.action(target) if row.node.read().public.winner is None)
            before=tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports())
            v.forecast(c.root)
            self.assertEqual(tuple((r.public_probability,r.probability,r.node.read()) for r in n.reports()),before)
            for r in n.reports()[:3]:self.assertEqual(r.node.export_request().roles(),r.node.read())

    def test_future_scan_keeps_exact_scalar_result_or_Pending_in_separate_path(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c=make('dual');v=PayoffVectorExperiment(c);h=next(h for h in c.root.read().private.hypotheses if h.roles[2]&1)
            known=tuple(a for a in h.acquisitions if a.player==1)
            for target in (4,3):
                n=c.root.personal(SeerObserver(1,known,2,target))[1]
                try:want=n.forecast()
                except Pending as old:
                    with self.assertRaises(Pending) as got:v.forecast(n)
                    self.assertEqual(got.exception.reason,old.reason)
                else:self.assertEqual(v.forecast(n),want)
            self.assertEqual(v.fallbacks,2)
            self.assertFalse(v.values);self.assertFalse(v.actions)

    def test_scope_and_warm_cancellation_work_limits_remain_separate(self):
        with calculation_budget(250000,max_seconds=30),kernel_calculation():
            c=make('dual');v=PayoffVectorExperiment(c);v.forecast(c.root)
            stop=Event();stop.set()
            with cancellation_scope(stop),self.assertRaises(CalculationCancelled):v.forecast(c.root)
            with calculation_budget(1),self.assertRaises(CalculationBudgetExceeded):v.forecast(c.root)
            with self.assertRaises(ValueError):v.forecast(make('dual').root)
            with self.assertRaises(ValueError):PayoffVectorExperiment(make('medium-pair'))

if __name__=='__main__':unittest.main()
