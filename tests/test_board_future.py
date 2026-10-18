import unittest
from contextlib import ExitStack
from dataclasses import asdict
from fractions import Fraction as F
from unittest.mock import patch
from tests.test_board_flow import game
from werewolf.board_flow import BoardData
from werewolf.exact import initial_board,Rules,Strategy,PublicEvent
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.evaluation_branch import ActionInputs,ContinuationInputs
from werewolf.action_flow import resolve_action

class GeneratedBoardTests(unittest.TestCase):
    def test_two_actions_replay_the_entire_evidence_and_share_game_data(self):
        b=initial_board(5,1);law=TrueScanState(from_board(b),initial_rule='none',tracked=())
        e=InformationSetForecast(Rules(initial_seer='none'),Strategy('random','random'))
        payload=ActionInputs(law,(),law,None,b)
        acquired,outcomes=resolve_action(b,payload,5,e.action_policy)
        continuing=next(o for o in outcomes if o.board.winner is None)
        first=e.action_policy.project(b,acquired,continuing,5)
        source=first.board_data
        acquired,outcomes=resolve_action(first.public,ActionInputs(first.public_state,first.past,
            first.private,first.observer,first.physical),4,e.action_policy)
        final=e.action_policy.project(first.public,acquired,outcomes[0],4)
        self.assertEqual(len(final.board_data.history),2)
        self.assertIs(final.board_data.origin,source.origin)
        self.assertIs(final.board_data.game_data,source.game_data)
        from werewolf.board_future import reconstruction_kernel_reuse
        with reconstruction_kernel_reuse(False), patch('werewolf.board_roles.project_generated',wraps=__import__(
                'werewolf.board_roles',fromlist=['project_generated']).project_generated) as replay:
            rebuilt=final.board_data.roles()
        self.assertEqual(rebuilt,final)
        self.assertEqual(replay.call_count,2)
        with reconstruction_kernel_reuse(True):reused=final.board_data.roles()
        self.assertEqual(reused,rebuilt)
        self.assertFalse(hasattr(final.board_data,'_completed'))
        self.assertTrue(any(op._completed and op._completed[2]>0 for op in final.board_data.history))
        self.assertEqual(sum(h.mass for h in rebuilt.public_state.hypotheses),1)

    def test_publication_and_actor_conditioning_match_previous_kernels(self):
        strategy=Strategy('max','random',fake_reports='random')
        source=game(seers=1,rules=asdict(Rules(initial_seer='none')),
                    policy=asdict(strategy),claims=['seer']+['latent']*4,
                    seer_mode='information-fixed-v1',
                    seer_options={'initial_rule':'none','likelihood':'compatibility'},seer_inputs=[])
        roles=BoardData.from_game(source).roles()
        generated=[]
        import werewolf.board_future as flow
        actual=flow.reconstruct_child
        def record(*args,**kwargs):
            value=actual(*args,**kwargs)
            if value.board_data is not None:generated.append(value.board_data)
            return value
        with patch.object(flow,'reconstruct_child',record):new=roles.forecast(max_seconds=20)
        self.assertTrue(generated)
        self.assertTrue(all(r.game_data is roles.owner.game_data for r in generated))
        # Disable the new orchestration only, preserving the pre-migration pure
        # role/publication kernels as an independent comparison calculation.
        def old_child(engine,board,payload,outcome,target,legacy):return legacy()
        def old_publication(engine,payload,child,public,past,private,physical,**kwargs):
            return ContinuationInputs(child,public,past,private,payload.observer,physical)
        roles.owner.runtime.clear()  # Exercise the independent kernels, not a completed Forecast hit.
        with ExitStack() as stack:
            stack.enter_context(patch.object(flow,'before_action',return_value=None))
            stack.enter_context(patch.object(flow,'record_publications',lambda e,b,s,p,rows,**kwargs:rows))
            stack.enter_context(patch.object(flow,'record_medium_instruction',return_value=None))
            stack.enter_context(patch.object(flow,'reconstruct_child',old_child))
            stack.enter_context(patch.object(flow,'reconstruct_publication',old_publication))
            old=roles.forecast(max_seconds=20)
        self.assertEqual(new,old)
        self.assertTrue(hasattr(new,'village_win'),new)

    def test_saved_terminal_board_stops_before_future_generation(self):
        source=game(players=3,claims=['latent']*3)
        root=BoardData.from_game(source)
        step=dict(target=3,policy=source['policy'],claims=source['claims'],claim_policy={})
        roles=root.child(step).roles()
        self.assertTrue(roles.progress.finished)
        with patch('werewolf.board_roles.prepare_evaluation',side_effect=AssertionError('future')):
            value=roles.forecast()
        self.assertEqual(value.village_win,F(1,3))
        self.assertEqual(value.action_values,())

    def test_actor_intervention_does_not_reuse_incompatible_actual_count_constraint(self):
        from dataclasses import replace
        from werewolf.exact import replace_worlds,PublicEvent
        from werewolf.actor_information import condition_actor_state
        from werewolf.evaluation_branch import physical_board
        from werewolf.board_future import condition_recipe
        base=initial_board(5,2,experimental_cast=True)
        public=replace_worlds(replace(base,alive=(1,2,3,4),wolf_count=None,phase='night',
            history=(PublicEvent(1,'day',5),)),
            ((17,0,0,0,F(1,2)),(3,0,0,0,F(1,2))))
        law=TrueScanState(from_board(public),initial_rule='none',tracked=())
        actual=condition_actor_state(law,lambda h:h.roles[0]==17)
        physical=replace_worlds(public,actual.public_roles,wolf_count=1)
        source=ContinuationInputs(public,law,(),actual,None,physical)
        assessed=condition_actor_state(law,lambda h:h.roles[0]==3)
        imagined=physical_board(public,assessed)
        target=ContinuationInputs(public,law,(),assessed,None,imagined)
        operation=condition_recipe(source,target)
        self.assertIsNotNone(operation)
        self.assertEqual(operation.physical_source,'intervention')
        reconstructed=operation(source)
        self.assertEqual(reconstructed.private,assessed)
        self.assertEqual(reconstructed.physical,imagined)
        self.assertEqual(source.physical.wolf_count,1)
        self.assertEqual(source.public_state,law)

    def test_existing_kernel_reuse_matches_cold_full_evidence_reconstruction(self):
        from werewolf.board_future import reconstruction_kernel_reuse
        strategy=Strategy('max','random',fake_reports='random')
        source=game(seers=1,rules=asdict(Rules(initial_seer='none')),
                    policy=asdict(strategy),claims=['seer']+['latent']*4,
                    seer_mode='information-fixed-v1',
                    seer_options={'initial_rule':'none','likelihood':'compatibility'},seer_inputs=[])
        roles=BoardData.from_game(source).roles()
        with reconstruction_kernel_reuse(False):reference=roles.forecast()
        with reconstruction_kernel_reuse(True):reused=roles.forecast()
        self.assertEqual(reference,reused)
        self.assertTrue(hasattr(reference,'village_win'),reference)

    def test_complete_input_keys_preserve_structural_equality_and_secret_histories(self):
        from dataclasses import replace
        from werewolf.board_future import evidence_key
        b=initial_board(5,1);state=TrueScanState(from_board(b),(b.alive,),initial_rule='none',tracked=())
        engine=InformationSetForecast(Rules(),Strategy())
        original=evidence_key(engine,(b,state))
        equal=evidence_key(engine,(replace(b),replace(state)))
        self.assertEqual(original,equal)
        self.assertEqual(hash(original),hash(equal))
        changed=replace(state,observed_prefix=1)
        self.assertNotEqual(original,evidence_key(engine,(b,changed)))
        from werewolf.seer_acquisition import acquire
        with_seer=initial_board(5,1,seer_count=1)
        seed=from_board(with_seer)
        left=acquire(seed,1,with_seer.alive,{p:p%5+1 for p in with_seer.alive})
        right=acquire(seed,1,with_seer.alive,{p:(p+1)%5+1 for p in with_seer.alive})
        law1=TrueScanState(left,(with_seer.alive,),initial_rule='normal')
        law2=TrueScanState(right,(with_seer.alive,),initial_rule='normal')
        self.assertEqual(law1.public_roles,law2.public_roles)
        self.assertNotEqual(evidence_key(engine,(with_seer,law1)),evidence_key(engine,(with_seer,law2)))

    def test_reusing_canonical_initial_physical_board_preserves_full_law(self):
        from werewolf.evaluation_branch import physical_board
        from werewolf.exact import replace_worlds
        b=initial_board(5,1,seer_count=1)
        law=TrueScanState(from_board(b),initial_rule='none',tracked=())
        self.assertEqual(physical_board(b,law),replace_worlds(b,law.public_roles))
        restricted=replace_worlds(b,(tuple(b.worlds[0][:-1])+(F(1),),),wolf_count=None)
        own=TrueScanState(from_board(restricted),initial_rule='none',tracked=())
        self.assertIs(physical_board(b,own,restricted),restricted)
        self.assertEqual(restricted.worlds,own.public_roles)

    def test_saved_seven_player_mixed_board_preserves_previous_complete_table(self):
        # Saved public Board, not the standalone public_forecast kernel route.
        # Corrected corpse rule: original shared-OFF and complete-key trial agree
        # on all rows (saved-corpse-comparisons.json); default budgets.
        from werewolf.by_dawn import HorizonValues
        source=game(players=7,wolves=2,mediums=2,seers=1,
            claims=['seer','medium','medium']+['latent']*4,
            rules=asdict(Rules(initial_seer='none')),policy=asdict(Strategy()),
            claim_policy={'medium':'none','seer':'none'},
            seer_mode='information-fixed-v1',
            seer_options={'initial_rule':'none','likelihood':'compatibility'},seer_inputs=[])
        result=BoardData.from_game(source).roles().forecast()
        self.assertTrue(hasattr(result,'village_win'),result)
        self.assertEqual(result.village_win,F(61,132))
        self.assertEqual(result.action_values,((1,F(47,108)),(2,F(61,132)),
            (3,F(61,132)),*((p,F(323,1008)) for p in range(4,8))))
        self.assertEqual(result.by_dawn_values,
            tuple((p,HorizonValues(F(0),F(0))) for p in range(1,8)))
        self.assertEqual(result.pending_metrics,())

    def test_saved_origin_reuse_matches_uncached_complete_reconstruction(self):
        from werewolf.board_future import SavedOrigin,reconstruction_kernel_reuse
        import werewolf.board_roles as roles
        data=BoardData.from_game(game(seers=1,rules=asdict(Rules(initial_seer='none')),
            claims=['seer']+['latent']*4,seer_mode='information-fixed-v1',
            seer_options={'initial_rule':'none','likelihood':'compatibility'},seer_inputs=[]))
        origin=SavedOrigin(data,data.game_data.rules,Strategy())
        with patch.object(roles,'prepare_evaluation',wraps=roles.prepare_evaluation) as prepare:
            first=origin();self.assertEqual(origin(),first)
            self.assertEqual(prepare.call_count,1)
            with reconstruction_kernel_reuse(False):reference=origin()
            self.assertEqual(prepare.call_count,2)
        self.assertEqual(first,reference)
        # A changed complete snapshot receives a distinct origin, never the old result.
        changed=SavedOrigin(data.updated(claims=['latent']*5),data.game_data.rules,Strategy())
        self.assertNotEqual(changed.board_data,origin.board_data)
        with reconstruction_kernel_reuse(False):expected=changed()
        self.assertEqual(changed(),expected)

    def test_saved_seven_player_observed_model_completes_the_http_request_budget(self):
        from app import create_app
        import json
        from pathlib import Path
        # Preserve the public log too: later CO observation is not an initial CO prior.
        source=json.loads((Path(__file__).parent/'fixtures'/'board_saved_seven_observed.json').read_text(encoding='utf-8'))
        app=create_app({'TESTING':True,'SECRET_KEY':'seven-http-regression',
            'HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True})
        client=app.test_client()
        with client.session_transaction() as session:session['game']=source
        response=client.get('/main')
        self.assertEqual(response.status_code,200)
        self.assertIn('data-fraction="157/693"',response.get_data(as_text=True))

    def test_count_sum_reuse_is_exact_and_caller_mutation_cannot_change_it(self):
        from dataclasses import replace
        b=initial_board(5,2,experimental_cast=True)
        before=hash(b)
        first=b.wolf_count_distribution;first.clear()
        self.assertEqual(b.wolf_count_distribution,{2:F(1)})
        self.assertEqual(hash(b),before)
        changed=replace(b,alive=(1,2,3,4),history=(PublicEvent(1,'day',5),),wolf_count=None)
        expected={}
        mask=sum(1<<(p-1) for p in changed.alive)
        for w,q in changed.belief:
            k=(w&mask).bit_count();expected[k]=expected.get(k,F())+q
        self.assertEqual(changed.wolf_count_distribution,expected)
