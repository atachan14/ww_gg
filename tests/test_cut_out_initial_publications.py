import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_initial_publications import base,scope,InitialPublicationEngine
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.actor_information import condition_actor_state
from werewolf.board_future import calculation_origin,remember
from werewolf.morning_publications import future_publications,public_report_branches
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import Pending


class InitialPublicationsTests(unittest.TestCase):
    def test_owned_initial_dispatch_and_first_morning_without_value_search(self):
        with calculation_budget(1000000,max_seconds=30):
            graph,w=base();root=scope(graph,w);e=InitialPublicationEngine(graph,witness=w)
            def forbidden(*args,**kwargs):raise AssertionError('unit must not run full root search')
            e.solve=e.act=forbidden
            with calculation_origin(graph.data):
                remember(e,graph.root,root)
                state,outcomes=resolve_action(root.public,ActionInputs(root.public_state,root.past,root.private,None,root.physical),3,e.action_policy)
                source=e.action_policy.project(root.public,state,outcomes[0],3)
                private=condition_actor_state(source.private,lambda h:h.roles[0]==17)
                payload=ActionInputs(source.public_state,source.past,private,None,physical_board(source.public,private,source.physical))
                acquired,outcomes=resolve_action(source.public,payload,4,e.action_policy)
                source=e.action_policy.project(source.public,acquired,outcomes[0],4)
                rows=e.morning(source.public,source.public_state,source.past)
                reference=public_report_branches(source.public,source.past,future_publications(source.public_state,source.past,source.public.alive,source.public.claims))
                key=lambda entries:{(b,p):(q,s) for q,b,s,p in entries}
                self.assertEqual(key(rows),key(reference))
                self.assertEqual(len(rows),64)
                self.assertEqual(e.values,{})
                self.assertEqual(len(e.publication_patterns),1)
                # Conservative published-event inheritance split the two COs.
                # The experiment cannot silently re-form an exchangeable group.
                _,b,s,p=rows[0]
                with self.assertRaises(Pending) as caught:e.generate_publications(b,s,p)
                self.assertIn('certified_group',caught.exception.reason)