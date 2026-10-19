import unittest
from dataclasses import replace
from fractions import Fraction as F
from threading import Event
from benchmarks.player_match_groups.dead_history_design import dead_two_seers
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.grouped_forecast import GroupedForecast
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.seer_acquisition import Acquisition
from werewolf.exact import Strategy
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget,cancellation_scope,CalculationCancelled


def engine(c,ordinary=False):
    cls=InformationSetForecast if ordinary else GroupedForecast
    e=cls(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False,**({} if ordinary else {'aggregate_reports':True}))
    e.retain_joint_guard_history=True
    return e


class DeadHistoryScalarTests(unittest.TestCase):
    def test_public_private_tables_named_actions_cold_and_cache_remain_full(self):
        c,n=dead_two_seers();s=n.read()
        h=next(h for h in s.private.hypotheses if any(a.player==1 and a.day==2 and a.target==3 and a.color=='black' for a in h.acquisitions))
        nodes=(n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(PersonalInformation(2,'seer',tuple(a for a in h.acquisitions if a.player==2)))[1],n.personal(WolfInformation.from_hypothesis(h))[1])
        e=engine(c)
        for node in nodes:
            source=node.read()
            with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                expected=forecast(engine(c,True),source);actual=forecast(e,source)
                self.assertEqual(actual,expected)
                self.assertEqual(tables(source,actual),tables(source,expected))
                self.assertEqual(forecast(e,source),actual)
                self.assertEqual(node.export_request().roles(),source)
                q,p=e.scalar_laws(source.public,source.public_state,source.private,source.observer)
                self.assertEqual(q.public_roles,source.public_state.public_roles)
                self.assertEqual(p.public_roles,source.private.public_roles)
                if source.observer is not None and source.observer.actor==1:
                    self.assertIs(q,source.public_state)
                    self.assertEqual(dict(actual.action_values)[3],1)
                    self.assertEqual(actual.village_win,F(1,3))
                else:self.assertEqual(len(q.hypotheses),3)
                self.assertEqual(e.report_children(source),engine(c,True).report_children(source))
            self.assertEqual(node.read(),source)
            self.assertEqual(len(source.public_state.hypotheses),12)
        self.assertTrue(e.scalar_projections)

    def test_quotient_cannot_create_support_for_an_unknown_dead_secret(self):
        c,n=dead_two_seers();source=n.read();h=source.private.hypotheses[0]
        records=tuple(Acquisition(a.day,a.player,4,'white') if a.player==1 and a.day==2 else a for a in h.acquisitions)
        bad=replace(source.private,hypotheses=(replace(h,mass=F(1),acquisitions=records),))
        e=engine(c)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30),self.assertRaises(Pending) as failure:
            e.solve(source.public,source.public_state,source.past,bad,None,physical=source.physical)
        self.assertEqual(failure.exception.reason,'information_set_report_likelihood_incomplete')
        self.assertFalse(e.values)

    def test_diagnostic_and_uniform_boundaries_keep_original_state(self):
        c,n=dead_two_seers();s=n.read();e=engine(c)
        for attr,value in (('trace',{}),('acquisition_provenance',object()),('aggregate_reports',False),('retire_uninformative_scans',True)):
            old=getattr(e,attr);setattr(e,attr,value)
            self.assertEqual(e.scalar_laws(s.public,s.public_state,s.private,s.observer),(s.public_state,s.private));setattr(e,attr,old)
        e.strategy=replace(e.strategy,day='random')
        self.assertEqual(e.scalar_laws(s.public,s.public_state,s.private,s.observer),(s.public_state,s.private))

    def test_warm_scalar_projection_polls_cancellation(self):
        c,n=dead_two_seers();s=n.read();e=engine(c)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):forecast(e,s)
        stop=Event();stop.set()
        with cancellation_scope(stop),self.assertRaises(CalculationCancelled):e.solve(*s,physical=s.physical)

if __name__=='__main__':unittest.main()
