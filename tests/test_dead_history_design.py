import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.dead_history_design import dead_two_seers,project,projected_state,DeadPublicExperiment
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.exact import Strategy
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget
from werewolf.seer_future_uniform import candidates


class DeadHistoryDesignTests(unittest.TestCase):
    def test_public_live_seer_wolf_and_dead_observer_are_distinct(self):
        c,n=dead_two_seers();s=n.read()
        h=next(h for h in s.private.hypotheses if any(a.player==1 and a.day==2 and a.target==3 and a.color=='black' for a in h.acquisitions))
        dead=n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
        live=n.personal(PersonalInformation(2,'seer',tuple(a for a in h.acquisitions if a.player==2)))[1]
        wolf=n.personal(WolfInformation.from_hypothesis(h))[1]
        self.assertEqual(len(s.public_state.hypotheses),12)
        self.assertEqual(len(project(s).public_state.hypotheses),3)
        self.assertEqual(len(project(wolf.read()).private.hypotheses),1)
        self.assertEqual(len(project(dead.read()).public_state.hypotheses),12)
        for node in (n,live,wolf,dead):
            source=node.read();reduced=project(source)
            with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                a=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
                b=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
                expected=forecast(a,source);actual=forecast(b,reduced)
                self.assertEqual(actual,expected)
                self.assertEqual(tables(source,actual),tables(source,expected))
            self.assertEqual(node.read(),source)
        # The dead owner's private best differs from the selected public policy.
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            f=forecast(InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False),dead.read())
        self.assertEqual(f.village_win,F(1,3));self.assertEqual(max(dict(f.action_values).values()),1)

    def test_blind_dead_owner_deletion_breaks_future_personal_observation(self):
        c,n=dead_two_seers();h=next(h for h in n.read().private.hypotheses if any(a.player==1 and a.day==2 and a.target==3 and a.color=='black' for a in h.acquisitions))
        node=n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
        source=node.read();bad=project(source,protect=False)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            e=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
            with self.assertRaises(Pending) as failure:forecast(e,bad)
            self.assertEqual(failure.exception.reason,'seer_view_scan_outside_public_support')

    def test_surviving_own_history_is_not_an_exchangeable_dead_record(self):
        c,n=dead_two_seers();source=n.read();reduced=project(source)
        for before,after in zip(source.public_state.hypotheses[:1],reduced.public_state.hypotheses[:1]):
            self.assertEqual(candidates(before,2,source.public_state.rosters[0]),candidates(after,2,reduced.public_state.rosters[0]))
            blind=projected_state(source.public_state,set())
            self.assertNotEqual(candidates(before,2,source.public_state.rosters[0]),candidates(blind.hypotheses[0],2,blind.rosters[0]))

    def test_next_public_payoff_moments_keep_private_measures_separate(self):
        from benchmarks.player_match_groups.report_integral_design import make,oracle
        from benchmarks.player_match_groups.dead_history_design import terminal_public_payoff_moments
        for kind,target in (('single',3),('dual',3),('three',4)):
            c,n=make(5,kind,target,5);h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
            nodes=(n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(WolfInformation.from_hypothesis(h))[1])
            public_moments=None
            for node in nodes:
                source=node.read()
                with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                    events,stats=oracle(source)
                    moments,qpi=terminal_public_payoff_moments(source,events)
                    if public_moments is None:public_moments=moments
                    self.assertEqual(moments,public_moments)
                    value=sum((h.mass*moments.get((h.roles,h.acquisitions),F())/qpi[h.roles,h.acquisitions] for h in source.private.hypotheses),F())
                    e=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
                    self.assertEqual(value,e.action_policy.morning_value(source))
                    self.assertTrue(all(F()<=m<=qpi[key] for key,m in moments.items()))

    def test_public_only_recursive_experiment_matches_ordinary_named_values(self):
        c,n=dead_two_seers();source=n.read()
        for selected in (source,):
            with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                a=InformationSetForecast(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
                b=DeadPublicExperiment(c.data.game_data.rules,Strategy(),exact_renaming=False,retire_uninformative_scans=False)
                self.assertEqual(forecast(a,selected),forecast(b,selected))
                self.assertGreater(b.visits['projected_calls'],0)

if __name__=='__main__':unittest.main()
