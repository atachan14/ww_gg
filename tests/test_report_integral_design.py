import unittest
from fractions import Fraction as F
from dataclasses import replace
from types import SimpleNamespace
from benchmarks.player_match_groups.report_integral_design import (make,run,audit,oracle,full,projection,factor_check,explicit_fake,enumerated_fake,compact_validation,compiled_mass_probe,five_full_terminal_sum,count_design_reference,medium_joint,normalized,terminal_named,Undefined)
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport
from werewolf.seer_future_uniform import TrueScanState,FuturePending
from werewolf.morning_publications import future_publications,plausible_fake_options,fake_backlog_options
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import Pending


class ReportIntegralDesignTests(unittest.TestCase):
    def setUp(self):
        self.budget=calculation_budget(250000,max_seconds=30);self.budget.__enter__()
    def tearDown(self):self.budget.__exit__(None,None,None)
    def test_complete_joint_oracle_and_constant_contraction_twelve_public_owner_cases(self):
        result=run();self.assertEqual(len(result['cases']),12)
        self.assertTrue(all(row['full_joint_oracle_equal'] and row['expanded']==row['contracted']=='1/3' for row in result['cases']))
    def test_observed_table_and_max_do_not_commute_with_unobserved_average(self):
        c,n=make(5,'single',3,5);s=n.read();rows,counts=audit(n);alive=s.public.alive
        before=terminal_named({full(h):h.mass for h in s.private.hypotheses},alive)
        after={event:terminal_named(row['P'],alive) for event,row in rows.items()}
        averaged={p:sum((rows[e]['p']*v[p] for e,v in after.items()),F()) for p in alive}
        self.assertEqual(averaged,before);self.assertEqual(before[2],F(1,2))
        chosen=next(e for e in rows if any(r.player==1 and r.acquired_day==2 and r.target==2 and r.color=='black' for r in e[1]))
        self.assertEqual(rows[chosen]['p'],F(1,6));self.assertEqual(after[chosen][2],1)
        self.assertEqual(max(before.values()),F(1,2))
        self.assertEqual(sum((rows[e]['p']*max(v.values()) for e,v in after.items()),F()),F(5,6))
        # Independent role payoff above agrees with actual physical executions.
        from werewolf.exact import action_outcomes
        for report in n.reports():
            t=report.node.read();key=(t.public.reports,t.past)
            physical={p:sum((o.probability*F(o.board.winner=='village') for o in action_outcomes(t.physical,p,c.data.game_data.rules,c._ClosedCalculation__engine.strategy)),F()) for p in alive}
            self.assertEqual(physical,after[key])
    def test_joint_reports_cannot_be_replaced_by_independent_marginals(self):
        c,n=make(5,'three',4,5);rows,counts=audit(n)
        self.assertEqual((counts['H'],counts['raw_emissions'],counts['public_vectors']),(27,135,109))
        cycle=((1,2),(2,3),(3,1));marginals=[]
        for p,target in cycle:
            marginals.append(sum((row['q'] for e,row in rows.items() if any(r.player==p and r.acquired_day==2 and r.target==target and r.color=='black' for r in e[1])),F()))
        joint=sum((row['q'] for e,row in rows.items() if all(any(r.player==p and r.acquired_day==2 and r.target==target and r.color=='black' for r in e[1]) for p,target in cycle)),F())
        self.assertEqual(marginals,[F(8,45)]*3);self.assertEqual(joint,0)
        self.assertEqual(marginals[0]*marginals[1]*marginals[2],F(512,91125))
    def test_medium_conditions_public_fake_kernel_before_seer_normalization(self):
        from benchmarks.player_match_groups.cut_out_user_seven_uniform_preparation import comparison_game
        from werewolf.closed_calculation import ClosedCalculation
        from werewolf.board_flow import BoardData
        from werewolf.actor_information import PersonalInformation
        c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        n=next(r.node for r in c.root.action(2) if r.node.read().public.winner is None)
        n=next(r.node for r in n.action(4) if r.node.read().public.winner is None);s=n.read()
        rows,counts=audit(n);self.assertEqual((counts['H'],counts['medium_families'],counts['raw_emissions'],counts['public_vectors']),(18,2,45,18))
        with self.assertRaisesRegex(Undefined,'design_constant_terminal_domain_required'):compiled_mass_probe(n)
        before=factor_check(s.public_state,s.past,s.public.alive,s.public.claims)
        self.assertEqual((before[(1,)]['raw_plans'],before[(1,)]['kept_plans'],before[(1,)]['Z']),(10,8,F(4,5)))
        for medium,weights in medium_joint(s).items():
            if medium[-1].color=='white':
                rules=factor_check(s.public_state,s.past,s.public.alive,s.public.claims,normalized(weights))
                self.assertEqual((rules[(1,)]['kept_plans'],rules[(1,)]['Z']),(10,F(1)))
        mass=sum((row['q'] for e,row in rows.items() if e[0][-1].color=='white' and any(r.player==1 and r.acquired_day==2 and r.target==2 and r.color=='white' for r in e[1])),F())
        self.assertEqual(mass,F(1,20))
        h=next(h for h in s.private.hypotheses if h.roles[2]&1)
        owner=n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
        own,_=audit(owner)
        self.assertTrue(any(e[0][-1].color=='white' and row['q']>0 and row['p']==0 for e,row in own.items()))
        self.assertEqual(len(compact_validation(owner.read())),2)
    def test_factored_normalizers_equal_current_selected_fake_law(self):
        for kind,day in [('dual',3),('three',4)]:
            c,n=make(5,kind,day,5);s=n.read();rules=factor_check(s.public_state,s.past,s.public.alive,s.public.claims)
            for fakes in rules:
                common=plausible_fake_options(s.public_state,fakes,s.past)
                self.assertNotIsInstance(common,FuturePending)
                self.assertEqual(dict(explicit_fake(s.public_state,s.past,fakes,rules)),dict(common))
            self.assertTrue(all(r['Z']==(F(1,2) if kind=='dual' else F(5,6)) for f,r in rules.items() if f))
            plain=factor_check(s.public_state,s.past,s.public.alive,s.public.claims,plausible=False)
            for fakes in plain:
                weights={full(h):h.mass for h in s.public_state.hypotheses}
                self.assertEqual(dict(explicit_fake(s.public_state,s.past,fakes,plain)),dict(enumerated_fake(s.public_state,s.past,fakes,weights,plausible=False)))
                self.assertEqual(dict(explicit_fake(s.public_state,s.past,fakes,plain)),dict(fake_backlog_options(s.public_state,fakes,s.past)))

    def test_missing_private_support_and_incomplete_event_family_are_not_completed(self):
        c,n=make(5,'single',3,5);s=n.read()
        bad=Hypothesis((16,0,1,0),(Acquisition(1,1,3,'white'),Acquisition(2,1,2,'white')),F(1))
        private=replace(s.private,hypotheses=(bad,));foreign=replace(s,private=private)
        with self.assertRaisesRegex(Undefined,'information_set_report_likelihood_incomplete'):compact_validation(foreign)
        e=c._ClosedCalculation__engine
        rows=e.morning(s.public,s.public_state,s.past)
        with self.assertRaises(Pending) as caught:e.push(s.public_state,private,rows)
        self.assertEqual(caught.exception.reason,'information_set_report_likelihood_incomplete')
        with self.assertRaises(Pending) as caught:e.push(s.public_state,s.private,rows[:-1])
        self.assertEqual(caught.exception.reason,'information_set_report_likelihood_incomplete')
    def test_undefined_raw_support_is_refused_instead_of_returning_a_constant(self):
        # Deliberately incoherent supplied public past, not a generated closed
        # source: dataclass normalization alone is insufficient for contraction.
        a=Hypothesis((2,0,1,0),(Acquisition(1,1,4,'white'),Acquisition(2,1,3,'white')),F(1,2))
        b=Hypothesis((1,0,2,0),(Acquisition(1,2,4,'white'),Acquisition(2,2,3,'white')),F(1,2))
        state=TrueScanState((b,a),((1,2,3,4,5),(1,2,3,4)))
        past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,4,'white'));alive=(1,2,3);claims=('seer','seer','latent','latent','latent')
        old=future_publications(state,past,alive,claims);self.assertIsInstance(old,FuturePending)
        self.assertEqual(old.reason,'no_noncontradictory_fake_report')
        with self.assertRaisesRegex(Undefined,old.reason):factor_check(state,past,alive,claims)
        from benchmarks.player_match_groups.closed_full_tree_fixture import case
        from werewolf.closed_calculation import ClosedCalculation
        one=ClosedCalculation(case(3,'single').data,grouped=True).root.read()
        with self.assertRaisesRegex(Undefined,'future_fake_law_does_not_specify_initial_declarations'):
            factor_check(one.public_state,one.past,one.public.alive,one.public.claims)
    def test_public_unsupported_family_cannot_be_pruned_by_private_zero_mass(self):
        a=Hypothesis((20,0,3,0),(Acquisition(1,1,4,'white'),Acquisition(1,2,4,'white'),Acquisition(2,1,3,'black'),Acquisition(2,2,1,'white')),F(1,2))
        b=Hypothesis((6,0,9,0),(Acquisition(1,1,4,'white'),Acquisition(1,4,1,'white'),Acquisition(2,1,2,'black'),Acquisition(2,4,2,'black')),F(1,2))
        state=TrueScanState((a,b),((1,2,3,4,5),)*2)
        past=tuple(SeerReport(1,1,p,4,'white') for p in (1,2,3));claims=('seer','seer','seer','latent','latent')
        old=future_publications(state,past,(1,2,3,4,5),claims)
        self.assertIsInstance(old,FuturePending);self.assertEqual(old.reason,'multiple_fake_report_correlation_unselected')
        with self.assertRaisesRegex(Undefined,old.reason):factor_check(state,past,(1,2,3,4,5),claims)
        # A P-only check misses the unsupported positive-Q world b.
        self.assertEqual(set(factor_check(state,past,(1,2,3,4,5),claims,{full(a):F(1)})),{(3,)})

    def test_coherent_but_delayed_backlog_can_have_zero_noncontradictory_normalizer(self):
        # Pure shared report-law input with repeated successful guards and
        # delayed reports. It is outside the admitted H0/full-disclosure scope.
        from werewolf.guard_effect import GuardIntent
        from werewolf.night_knowledge import WolfAttack
        guards=tuple(GuardIntent(n,4,3) for n in (1,2,3));attacks=tuple(WolfAttack(n,3) for n in (1,2,3))
        a=Hypothesis((2,0,1,8),(Acquisition(1,1,4,'white'),Acquisition(2,1,2,'black'),Acquisition(3,1,3,'white'),Acquisition(4,1,4,'white')),F(1,2),guards,attacks)
        b=Hypothesis((1,0,2,8),(Acquisition(1,2,4,'white'),Acquisition(2,2,1,'black'),Acquisition(3,2,3,'white'),Acquisition(4,2,4,'white')),F(1,2),guards,attacks)
        state=TrueScanState((b,a),((1,2,3,4),)*4)
        past=tuple(SeerReport(1,1,p,4,'white') for p in (1,2));claims=('seer','seer','latent','latent')
        old=future_publications(state,past,(1,2,3,4),claims)
        self.assertIsInstance(old,FuturePending);self.assertEqual(old.reason,'no_noncontradictory_fake_report')
        with self.assertRaisesRegex(Undefined,old.reason):factor_check(state,past,(1,2,3,4),claims)
        self.assertNotIsInstance(future_publications(state,past,(1,2,3,4),claims,fake_policy=('uniform',)),FuturePending)
        plain=factor_check(state,past,(1,2,3,4),claims,plausible=False)
        self.assertEqual({r['raw_plans'] for r in plain.values()},{64})

    def test_multiple_night_complete_prefix_retains_one_pending_slot_and_truth_witness(self):
        from benchmarks.player_match_groups.cut_out_user_seven_uniform_preparation import comparison_game
        from werewolf.closed_calculation import ClosedCalculation
        from werewolf.board_flow import BoardData
        from werewolf.actor_information import PersonalInformation,WolfInformation
        c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        n=next(r.node for r in c.root.action(4) if r.node.read().public.winner is None)
        n=next(r.node for r in n.action(3) if r.node.read().public.winner is None)
        n=next(r.node for r in n.reports() if all(any(a.acquired_day==2 and a.player==p and a.target==3 and a.color=='white' for a in r.node.read().past) for p in (1,2)))
        n=next(r.node for r in n.action(5) if r.node.read().public.winner is None)
        n=next(r.node for r in n.action(7) if r.node.read().public.winner is None)
        h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
        for selected in (n,n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],n.personal(WolfInformation.from_hypothesis(h))[1]):
            rows,counts=audit(selected)
            self.assertEqual((counts['H'],counts['raw_emissions'],counts['public_vectors']),(8,32,16))
            self.assertEqual(sum((r['p']*sum(terminal_named(r['P'],selected.read().public.alive).values(),F())/3 for r in rows.values() if r['p']),F()),F(1,3))
            candidate,probe=compiled_mass_probe(selected);self.assertEqual(candidate,F(1,3));self.assertEqual(probe['built_conditional_seer_event_laws'],0)
            families=compact_validation(selected.read())
            for medium,rules in families:
                for fakes,rule in rules.items():
                    if fakes:
                        self.assertEqual(len(rule['factor_slots']),1)
                        self.assertEqual(rule['Z'],F(1,2))
                        self.assertGreater(rule['kept_plans'],0)

    def test_support_existence_does_not_reweight_by_hypothetical_truth_frequency(self):
        c,n=make(5,'three',4,5);s=n.read();choices=plausible_fake_options(s.public_state,(1,),s.past)
        q=next(q for plan,q in choices if any(r.acquired_day==2 and r.target==5 and r.color=='white' for r in plan))
        truth_mass=sum((h.mass for h in s.public_state.hypotheses if h.roles[2]&1),F())
        truth_signature_mass=sum((h.mass for h in s.public_state.hypotheses if h.roles[2]&1 and any(a.player==1 and a.day==2 and a.target==5 for a in h.acquisitions)),F())
        self.assertEqual(q,F(1,5));self.assertEqual(truth_signature_mass/truth_mass,F(1,3))

    def test_broader_uniform_count_candidate_matches_complete_named_five_player_integrals(self):
        from benchmarks.player_match_groups.closed_full_tree_fixture import case
        from werewolf.closed_calculation import ClosedCalculation
        from werewolf.actor_information import PersonalInformation,WolfInformation
        from unittest.mock import patch
        for kind in ('single','dual','three','medium-pair'):
            c=ClosedCalculation(case(5,kind).data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
            h=next(h for h in c.root.read().private.hypotheses if h.roles[2]&1)
            nodes=(c.root,c.root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],c.root.personal(WolfInformation.from_hypothesis(h))[1])
            for n in nodes:
                with patch.object(c._ClosedCalculation__engine,'solve',side_effect=AssertionError('reference calls count solver')):
                    value,columns,stats=five_full_terminal_sum(n)
                expected,expected_columns=count_design_reference(n)
                self.assertEqual(value,F(7,15));self.assertEqual((value,columns),(expected,expected_columns))
                ordinary=n.forecast();self.assertEqual(ordinary.village_win,value);self.assertEqual(dict(ordinary.action_values),columns)
    def test_prospective_scan_intervention_prevents_unconditional_count_shortcut(self):
        from benchmarks.player_match_groups.closed_full_tree_fixture import case
        from werewolf.closed_calculation import ClosedCalculation
        from werewolf.seer_intervention import SeerObserver
        c=ClosedCalculation(case(5,'single').data,grouped=True)
        h=c.root.read().private.hypotheses[0]
        info=SeerObserver(1,tuple(a for a in h.acquisitions if a.player==1),2,3)
        n=c.root.personal(info)[1]
        with self.assertRaisesRegex(Undefined,'design_prospective_observer_excluded'):count_design_reference(n)
        with self.assertRaises(Pending) as caught:n.forecast()
        self.assertEqual(caught.exception.reason,'seer_view_scan_outside_public_support')

    def test_mixed_live_counts_keep_actual_P_weights_and_roster_choice_contributions(self):
        from benchmarks.player_match_groups.closed_full_tree_fixture import case
        from werewolf.closed_calculation import ClosedCalculation
        from werewolf.board_flow import BoardData
        from werewolf.actor_information import WolfInformation
        from werewolf.information_set_forecast import exchangeable_value
        g=case(6,'dual').data.to_game();g['wolves']=2
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        n=c.root.observe(6)[1];s=n.read();e=c._ClosedCalculation__engine
        self.assertEqual(s.physical.wolf_count_distribution,{1:F(1,3),2:F(2,3)})
        value,columns=count_design_reference(n);actual=n.forecast()
        self.assertEqual(value,F(1,12));self.assertEqual(value,actual.village_win);self.assertEqual(columns,dict(actual.action_values))
        contributions={p:F() for p in s.public.alive}
        for choice in n.wolf_choices():
            world=choice.node.read();count=next(iter(world.physical.wolf_count_distribution))
            contributions[choice.target]+=choice.mass*exchangeable_value(4,count,'day',e.strategy)
        self.assertEqual(sum(contributions.values(),F()),value)
        self.assertEqual(contributions[1],F(1,96));self.assertEqual(contributions[3],F(1,48))
        self.assertNotEqual(contributions[1],value/len(columns))
        h=next(h for h in s.private.hypotheses if (h.roles[0]&s.public.alive_mask).bit_count()==2)
        owner=n.personal(WolfInformation.from_hypothesis(h))[1]
        self.assertEqual(count_design_reference(owner)[0],0);self.assertEqual(owner.forecast().village_win,0)
