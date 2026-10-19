import unittest
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.max_structure_design import calculation,actual_report_frames,invariant,AuditedRefinedExperiment,RefinedMaxOrbitExperiment
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from tests.test_terminal_max_report import ordinary
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget
from werewolf.actor_information import PersonalInformation
from werewolf.group_partition import _report_groups


class MaxStructureDesignTests(unittest.TestCase):
    def test_orbit_sizes_and_owned_information_precede_max(self):
        # Equal PUBLIC scores, but P differs between two invariant orbits.
        scores={1:F(1,3),2:F(1,3),3:F(1,3)}
        payoffs={1:F(1,2),2:F(1,4),3:F(1,4)}
        exact=sum(payoffs.values(),F())/len(scores)
        representative=(payoffs[1]+2*payoffs[2])/3
        wrong=(payoffs[1]+payoffs[2])/2
        self.assertEqual(exact,representative);self.assertNotEqual(exact,wrong)
        # Team I is known BEFORE choosing a bite. Transform each team's whole
        # policy, rather than pooling distinct information sets before min.
        rows=((F(0),F(1)),(F(1),F(0)))
        self.assertEqual(sum(min(row) for row in rows)/2,0)
        self.assertEqual(min(sum(row[t] for row in rows)/2 for t in (0,1)),F(1,2))

    def test_private_seer_splits_otherwise_equal_public_claimants(self):
        c,n=calculation('dual','orbits');e=c._ClosedCalculation__engine
        for target in (3,5):n=next(r.node for r in n.action(target) if r.node.read().public.winner is None)
        h=next(h for h in n.read().private.hypotheses if h.roles[2]&1)
        own=n.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
        self.assertTrue(invariant(n.read(),n.groups))
        self.assertFalse(invariant(own.read(),n.groups))
        self.assertTrue(invariant(own.read(),own.groups))
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            public,old=ordinary(n.read(),e.rules);private,old=ordinary(own.read(),e.rules)
            self.assertEqual(dict(public.action_values)[1],dict(public.action_values)[2])
            self.assertEqual(dict(private.action_values)[1],0);self.assertEqual(dict(private.action_values)[2],1)
            self.assertEqual(private.village_win,F(1,2))
            self.assertEqual(own.forecast(),private)

    def test_full_completed_small_views_with_independent_frame_audit(self):
        for kind in ('single','dual','three','medium-pair'):
            for view in ('public','seer','wolf'):
                c,n=calculation(kind,'orbits',view);e=c._ClosedCalculation__engine;e.__class__=AuditedRefinedExperiment
                with kernel_calculation(),calculation_budget(250000,max_seconds=30):
                    want,old=ordinary(n.read(),e.rules);actual=n.forecast()
                    self.assertEqual(actual,want);self.assertEqual(tables(n.read(),actual),tables(n.read(),want))
                    self.assertEqual(n.export_request().roles(),n.read())
                    self.assertTrue(e.audited_frames)

    def test_stale_groups_fail_after_public_reports_and_common_refinement_fixes_them(self):
        c,n,frames=actual_report_frames()
        self.assertEqual(len(n.read().public.alive),5)
        stale=[s for s in frames if not invariant(s,n.groups)]
        self.assertEqual(len(frames),49);self.assertEqual(len(stale),46)
        self.assertTrue(all(invariant(s,_report_groups(n.groups,s)) for s in frames))
        e=c._ClosedCalculation__engine;e.__class__=RefinedMaxOrbitExperiment
        observed=[];s=stale[0]
        def record_solve(*args,**kw):observed.append(e.groups);return F()
        with e.group_scope(n.groups),patch.object(e,'solve',side_effect=record_solve):e.scalar(s.public,s.public_state,s.past)
        self.assertEqual(observed,[_report_groups(n.groups,s)])

    def test_horizon_named_execution_history_must_refine_the_actor_group(self):
        from werewolf.actor_information import WolfInformation
        from werewolf.evaluation_branch import ContinuationInputs,physical_board
        from werewolf.group_partition import _fix
        c,root=calculation('single','orbits');e=c._ClosedCalculation__engine
        node=next(r.node for r in root.action(2) if r.node.read().public.winner is None)
        source=node.read();info=WolfInformation.from_hypothesis(source.private.hypotheses[0])
        own=info.condition_public(source.public_state)
        frame=ContinuationInputs(source.public,source.public_state,source.past,own,None,physical_board(source.public,own))
        with e.group_scope(root.groups),e.actor_scope(info):self.assertFalse(invariant(frame,e.groups))
        with e.group_scope(_fix(root.groups,(event.target for event in source.public.history))),e.actor_scope(info):
            self.assertTrue(invariant(frame,e.groups))

    def test_nonterminal_two_wolf_reported_frame_has_complete_named_comparison(self):
        c,n,frames=actual_report_frames();e=c._ClosedCalculation__engine;e.__class__=AuditedRefinedExperiment
        s=next(s for s in frames if all(r.acquired_day!=2 or r.target==3 for r in s.past))
        groups=_report_groups(n.groups,s)
        self.assertTrue(any(len(g)>1 for g in groups))
        from werewolf.actor_information import WolfInformation
        from werewolf.group_partition import _fix
        h=next(h for h in s.private.hypotheses if h.roles[2]&1)
        infos=(None,PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)),WolfInformation.from_hypothesis(h))
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            for info in infos:
                source=s if info is None else e.personal_view(s,info)[1]
                fixed=() if info is None else (info.actor,*(a.target for a in info.acquisitions)) if type(info)is PersonalInformation else tuple(p for p in range(1,8) if info.initial_roster&(1<<(p-1)))+tuple(a.target for a in info.attacks)
                with e.group_scope(_fix(groups,fixed)):
                    want,old=ordinary(source,e.rules);actual=forecast(e,source)
                    self.assertEqual(actual,want);self.assertEqual(tables(source,actual),tables(source,want))
                    self.assertTrue(e.audited_frames)

if __name__=='__main__':unittest.main()
