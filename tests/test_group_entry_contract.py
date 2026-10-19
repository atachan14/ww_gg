import unittest
from dataclasses import asdict,replace
from types import SimpleNamespace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from benchmarks.player_match_groups.closed_saved_day_fixture import saved_day
from benchmarks.player_match_groups.max_structure_design import invariant,actual_report_frames
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import forecast,tables
from tests.test_terminal_max_report import ordinary
from werewolf.closed_calculation import ClosedCalculation
from werewolf.group_partition import _frame_groups
from werewolf.grouped_forecast import GroupedForecast
from werewolf.exact import Strategy,MediumReport,PublicEvent
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.seer_intervention import SeerObserver
from werewolf.board_future import kernel_calculation
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import Pending


def closed(data):return ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,max_work=250000,max_seconds=30)


class EntryAuditedForecast(GroupedForecast):
    def check_frame(self,b,s,past,p,observer,physical):
        from werewolf.evaluation_branch import ContinuationInputs,physical_board
        frame=ContinuationInputs(b,s,past,p,observer,physical_board(b,p,physical))
        if not hasattr(self,'entry_frame_audits'):self.entry_frame_audits=set()
        key=(frame,self.groups)
        if key not in self.entry_frame_audits:
            assert invariant(frame,self.groups),'full constructed-frame invariance failed'
            self.entry_frame_audits.add(key)
    def solve(self,b,s,past,p,observer,*,physical=None):
        with self.frame_scope(b,past,observer):
            self.check_frame(b,s,past,p,observer,physical)
            return super().solve(b,s,past,p,observer,physical=physical)
    def act(self,b,s,past,target,p,observer,*,physical=None):
        with self.frame_scope(b,past,observer,target=target):
            self.check_frame(b,s,past,p,observer,physical)
            return super().act(b,s,past,target,p,observer,physical=physical)


class GroupEntryContractTests(unittest.TestCase):
    def compare(self,node,c):
        s=node.read();e=c._ClosedCalculation__engine
        self.assertTrue(invariant(s,node.groups))
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            want,old=self.reference(s,e)
            got=node.forecast();self.assertEqual(got,want);self.assertEqual(tables(s,got),tables(s,want))
            self.assertEqual(node.export_request().roles(),s);self.assertEqual(node.forecast(),got)
        self.assertEqual(node.read(),s)
    def reference(self,s,engine):
        from werewolf.information_set_forecast import InformationSetForecast
        e=InformationSetForecast(engine.rules,engine.strategy,exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
        # Development reference: enumerate named actions/team cells, keep full
        # histories and exact-context memoization, disable all relabel/count
        # shortcuts. Chance/legal/policy operations remain the common ones.
        e.equivalent_targets=lambda *args:False
        e.actor_equivalent_targets=lambda *args:False
        e.exchangeable=lambda board:False
        e.renamed_value_key=lambda *args,**kw:None
        e.full_renamed_key=lambda *args,**kw:None
        e.scalar_descriptor=lambda *args,**kw:None
        e.value_law=lambda state:state
        return forecast(e,s),e

    def test_all_public_event_refinements_and_equal_simultaneous_meaning(self):
        base=SimpleNamespace(player_count=5,alive=(1,2,3,4,5),history=(),reports=(),report_resolved=(),medium_opportunities=())
        groups=((1,2),(3,4),(5,))
        same=(SeerReport(2,2,1,5,'white'),SeerReport(2,2,2,5,'white'))
        self.assertIn((1,2),_frame_groups(groups,base,same))
        for rows in (same[:1],(same[0],replace(same[1],color='black')),(same[0],replace(same[1],published_day=3)),(*same,SeerReport(2,2,3,1,'white'))):
            self.assertNotIn((1,2),_frame_groups(groups,base,rows))
        for field,one,both in (
            ('reports',(MediumReport(2,1,5,'white'),),(MediumReport(2,1,5,'white'),MediumReport(2,2,5,'white'))),
            ('report_resolved',((2,1,5),),((2,1,5),(2,2,5))),
            ('medium_opportunities',((2,1,5),),((2,1,5),(2,2,5)))):
            self.assertNotIn((1,2),_frame_groups(groups,SimpleNamespace(**{**vars(base),field:one}),()))
            self.assertIn((1,2),_frame_groups(groups,SimpleNamespace(**{**vars(base),field:both}),()))
        for changes in ({'history':(PublicEvent(1,'day',1),)}, {'alive':(2,3,4,5)}):
            self.assertNotIn((1,2),_frame_groups(groups,SimpleNamespace(**{**vars(base),**changes}),()))
        self.assertNotIn((1,2),_frame_groups(groups,base,(),PersonalInformation(1,'seer')))
        self.assertNotIn((1,2),_frame_groups(groups,base,(),SeerObserver(3,(),2,1)))
        child=_frame_groups(((1,),(2,),(3,4),(5,)),base,same);self.assertNotIn((1,2),child)
        self.assertEqual(_frame_groups(child,base,same),child)

    def test_initial_public_owner_and_horizon_use_the_same_frame_contract(self):
        for kind in ('single','dual','three','medium-pair'):
            c=closed(case(5,kind).data.updated(policy=asdict(Strategy())));e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast
            root=c.root;h=next(h for h in root.read().private.hypotheses if h.roles[2]&1)
            nodes=(root,root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1],root.personal(WolfInformation.from_hypothesis(h))[1])
            for node in reversed(nodes):self.compare(node,c)
            self.assertTrue(e.entry_frame_audits)

    def test_report_candidate_direct_scalar_and_actual_report_entry(self):
        c,n,frames=actual_report_frames();e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast
        stale=[s for s in frames if not invariant(s,n.groups)];self.assertEqual(len(stale),46)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30),e.group_scope(n.groups):
            for child in frames:
                with e.frame_scope(child.public,child.past,child.observer):self.assertTrue(invariant(child,e.groups))
            for s in (stale[0],stale[-1]):
                e.scalar(s.public,s.public_state,s.past)
            self.assertTrue(e.entry_frame_audits)
        c=closed(case(5,'dual').data.updated(policy=asdict(Strategy())));n=c.root
        for t in (3,5):n=next(r.node for r in n.action(t) if r.node.read().public.winner is None)
        branches=n.reports()
        for branch in branches:
            self.compare(branch.node,c)
            current=tuple(r for r in branch.node.read().past if r.published_day==2)
            mass,observed=n.observe_reports(current,branch.node.read().public.reports)
            self.assertEqual(observed.read(),branch.node.read());self.assertEqual(observed.groups,branch.node.groups)
            self.assertEqual(observed.export_request().roles(),observed.read())

    def test_live_multiple_nights_owner_future_and_cold(self):
        from benchmarks.player_match_groups.closed_saved_history_fixture import case as history_case
        graph,targets=history_case(7);data=graph.data.updated(policy=asdict(Strategy()))
        c=closed(data);e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast;n=c.root
        # Forced named paths preserve actual identities and are not observed
        # policy-choice replay. No seven-player Forecast is requested.
        for t in targets:
            n=next(r.node for r in n.action(t) if r.node.read().public.winner is None)
            self.assertTrue(invariant(n.read(),n.groups));self.assertEqual(n.export_request().roles(),n.read())
        self.compare(n,c)
        h=n.read().private.hypotheses[0]
        wolf=n.personal(WolfInformation.from_hypothesis(h))[1];self.compare(wolf,c)
        c=closed(case(5,'single').data.updated(policy=asdict(Strategy())));e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast
        h=c.root.read().private.hypotheses[0];initial=tuple(a for a in h.acquisitions if a.player==1)
        valid=c.root.personal(SeerObserver(1,initial,2,2))[1];self.compare(valid,c)
        invalid=c.root.personal(SeerObserver(1,initial,2,3))[1]
        with self.assertRaises(Pending):invalid.forecast()

    def test_saved_uniform_reopen_edit_cancel_recalculate_and_observed_cold(self):
        from benchmarks.player_match_groups.closed_morning_reports_fixture import case as reports_case,report_vector
        graph,targets=reports_case(5);data=graph.data;c=closed(data);node=c.root;prob=F(1)
        for index,t in enumerate(targets):
            mass,node=node.observe(t);prob*=mass;data=saved_day(data,t)
            if index==1:
                with self.assertRaisesRegex(Pending,'new_seer_report'):closed(data)
                continue
            reopened=closed(data)
            self.assertEqual(reopened.root.read(),node.read());self.assertEqual(reopened.root.groups,node.groups)
            self.assertEqual(reopened.entry_probability,prob);self.compare(reopened.root,reopened)
        rows=report_vector(5);mass,observed=node.observe_reports(rows)
        current=data.updated(seer_inputs=data.to_game()['seer_inputs']+[dict(day=2,reporter=r.player,target=r.target,color=r.color) for r in rows])
        reopened=closed(current);self.assertEqual(reopened.root.read(),observed.read());self.assertEqual(reopened.root.groups,observed.groups)
        self.assertIn((1,2),reopened.root.groups);self.compare(reopened.root,reopened)
        asymmetric=(rows[0],replace(rows[1],target=1,color='black'))
        edited=data.updated(seer_inputs=data.to_game()['seer_inputs']+[dict(day=2,reporter=r.player,target=r.target,color=r.color) for r in asymmetric])
        changed=closed(edited);self.assertNotIn((1,2),changed.root.groups);self.compare(changed.root,changed)
        cancelled=closed(data.updated(history=data.to_game()['history'][:-1]));self.assertEqual(cancelled.root.read().public.phase,'night')
        self.compare(cancelled.root,cancelled);self.assertEqual(reopened.root.export_request().roles(),observed.read())

    def test_latent_seer_and_named_wolf_choices_keep_observer_information(self):
        from werewolf.board_flow import BoardData
        game=case(5,'single').data.to_game();game.update(claims=['latent']*5,seer_inputs=[],
            claim_policy=dict(seer='none',medium='none',villager='none',wolf='none'),policy=asdict(Strategy()))
        c=closed(BoardData.from_game(game));e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast
        h=next(h for h in c.root.read().private.hypotheses if h.roles[2]&1)
        owner=c.root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]
        self.compare(c.root,c);self.compare(owner,c)
        night=next(r.node for r in c.root.action(2) if r.node.read().public.winner is None)
        with kernel_calculation(),calculation_budget(250000,max_seconds=30):
            want,old=self.reference(night.read(),e)
            actual=night.wolf_choices();expected=old.wolf_choices(night.read())
            self.assertEqual(tuple((r.mass,r.target,r.node.read()) for r in actual),tuple((mass,target,child) for mass,child,target,unused in expected))
            for row in actual:
                self.assertTrue(invariant(row.node.read(),row.node.groups))
                self.assertEqual(row.node.export_request().roles(),row.node.read())

    def test_owner_death_cancels_only_future_scan_and_cold_keeps_known_record(self):
        c=closed(case(5,'single').data.updated(policy=asdict(Strategy())));e=c._ClosedCalculation__engine;e.__class__=EntryAuditedForecast
        h=next(h for h in c.root.read().private.hypotheses if h.roles[2]&1)
        known=tuple(a for a in h.acquisitions if a.player==1)
        owner=c.root.personal(SeerObserver(1,known,2,2))[1]
        night=next(r.node for r in owner.action(1) if r.node.read().public.winner is None)
        self.assertNotIn(1,night.read().public.alive)
        self.assertTrue(all(all(a in row.acquisitions for a in known) for row in night.read().private.hypotheses))
        self.compare(night,c)

    def test_unsupported_inputs_and_diagnostic_scopes_do_not_expand(self):
        from werewolf.board_flow import BoardData
        game=case(5,'single').data.to_game();game.update(hunters=1,policy=asdict(Strategy()))
        with self.assertRaises(Pending):closed(BoardData.from_game(game))
        c=closed(case(5,'single').data.updated(policy=asdict(Strategy())));e=c._ClosedCalculation__engine
        self.assertTrue(e.max_grouped)
        for name,value in (('trace',{}),('retire_uninformative_scans',True),('aggregate_wolf',False),('aggregate_reports',False),('acquisition_provenance',object())):
            previous=getattr(e,name);setattr(e,name,value);self.assertFalse(e.max_grouped);setattr(e,name,previous)
        self.assertEqual(_frame_groups(c.root.groups,c.root.read().public,c.root.read().past,lambda *args:True),())
        game=c.data.to_game();game['rules']['allow_self_bite']=True;game['policy']=asdict(replace(Strategy(),include_self_bite=True))
        self_bite=closed(BoardData.from_game(game))
        with self.assertRaisesRegex(Pending,'self_bite'):self_bite.root.forecast()

    def test_max_initial_edit_is_new_calculation_and_saved_max_remains_declined(self):
        data=case(5,'dual').data.updated(policy=asdict(Strategy()));old=closed(data);before=old.root.read();want=old.root.forecast()
        changed=data.updated(seer_inputs=[{**r,'target':4} for r in data.to_game()['seer_inputs']])
        new=closed(changed);self.assertIsNot(old._ClosedCalculation__engine.terminal_moments,new._ClosedCalculation__engine.terminal_moments)
        self.assertNotEqual(old.root.groups,new.root.groups);self.compare(new.root,new)
        original=data.to_game()['seer_inputs']
        side=closed(data.updated(seer_inputs=[original[0],{**original[1],'target':4}]))
        self.assertIn((1,2),old.root.groups);self.assertNotIn((1,2),side.root.groups)
        self.compare(side.root,side)
        self.assertEqual(closed(data).root.read(),before);self.assertEqual(old.root.forecast(),want)
        with self.assertRaisesRegex(Pending,'saved_action_uniform_H0_only'):closed(saved_day(data,3))
        with self.assertRaisesRegex(Pending,'saved_action_uniform_H0_only'):old.root.observe(3)

if __name__=='__main__':unittest.main()
