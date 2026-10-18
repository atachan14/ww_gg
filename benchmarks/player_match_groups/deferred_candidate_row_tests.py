import unittest
from fractions import Fraction as F
from dataclasses import replace
from werewolf.exact import Rules,Strategy,initial_board
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.wolf_profile_certificate import WolfProfileResolver
from werewolf.policy_dependencies import Dependency,DependencyGraph

class CandidateRowResumeTests(unittest.TestCase):
    def fixture(self):
        e=WolfProfileResolver(Rules(),Strategy(),candidate_row_reuse=True)
        b=initial_board(6,1);from werewolf.seer_acquisition import from_board
        s=TrueScanState(from_board(b))
        return e,b,s
    def test_complete_source_graph_stack_and_probe_mode_remain_separate(self):
        e,b,s=self.fixture();source=e.candidate_row_source(b,s,(),e.rules,e.strategy)
        value=(F(1,3),2);e.candidate_row_store(source,('full-row',),False,value)
        self.assertEqual(e.candidate_row_get(source,('full-row',),False),value)
        self.assertIsNone(e.candidate_row_get(source,('full-row',),True))
        changed=e.candidate_row_source(b,replace(s,initial_rule='none'),(),e.rules,e.strategy)
        self.assertIsNone(e.candidate_row_get(changed,('full-row',),False))
        e.dependencies.stack.append(Dependency('other-ancestor',()))
        changed=e.candidate_row_source(b,s,(),e.rules,e.strategy)
        self.assertIsNone(e.candidate_row_get(changed,('full-row',),False))
        e.dependencies.stack.pop();e.dependencies=DependencyGraph()
        changed=e.candidate_row_source(b,s,(),e.rules,e.strategy)
        self.assertIsNone(e.candidate_row_get(changed,('full-row',),False))
    def test_bounds_cleanup_and_invalid_values(self):
        e,b,s=self.fixture();source=e.candidate_row_source(b,s,(),e.rules,e.strategy)
        e.candidate_row_store(source,('bad',),False,(None,0))
        self.assertFalse(e.completed_candidate_rows)
        for n in range(600):e.candidate_row_store(source,('row',n),False,(F(1,2),0))
        self.assertLessEqual(len(e.completed_candidate_rows),512)
        self.assertLessEqual(e.candidate_row_weight,8000)
        e.discard_candidate_rows(b,s,())
        self.assertFalse(e.completed_candidate_rows);self.assertFalse(e.candidate_row_sources)
        self.assertEqual(e.candidate_row_weight,0)
    def test_default_is_not_automatic_ui_resume(self):
        from werewolf.local_reuse import reuse_scope
        with reuse_scope(True):e=WolfProfileResolver(Rules(),Strategy())
        self.assertFalse(e.candidate_row_reuse)
        self.assertIsNone(e.candidate_row_source(initial_board(6,1),None,(),e.rules,e.strategy))

    def test_explicit_verification_capacity_is_bounded(self):
        with self.assertRaises(ValueError):WolfProfileResolver(Rules(),Strategy(),candidate_row_state_limit=32001)
        e=WolfProfileResolver(Rules(),Strategy(),candidate_row_reuse=True,candidate_row_state_limit=32000)
        self.assertEqual(e.candidate_row_state_limit,32000)
