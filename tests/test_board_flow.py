import copy,json,unittest
from dataclasses import asdict
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.board_flow import BoardData
from werewolf.exact import Rules,Strategy
from tests.fixtures.board_replay_v051 import reconstruct_saved as old_replay


def game(**changes):
    value=dict(players=5,wolves=1,mediums=0,seers=0,hunters=0,
               rules=asdict(Rules()),policy=asdict(Strategy()),history=[],
               claims=['latent']*5,claim_policy={},selection=None,revision=0)
    value.update(changes)
    return value

class BoardFlowTests(unittest.TestCase):
    def test_common_data_is_shared_and_inputs_are_an_evidence_snapshot(self):
        source=game();root=BoardData.from_game(source)
        changed=root.updated(selection=2,revision=1)
        step=dict(target=5,policy=source['policy'],claims=source['claims'],claim_policy={})
        child=root.child(step)
        self.assertIs(root.game_data,changed.game_data)
        self.assertIs(root.game_data,child.game_data)
        self.assertFalse(set(json.loads(root.inputs))&{'players','wolves','rules'})
        source['claims'][0]='wolf'
        self.assertEqual(root.to_game()['claims'],['latent']*5)
        with self.assertRaises(ValueError):root.updated(rules={})
        self.assertEqual(child.facts.alive,(1,2,3,4))
        self.assertEqual(child.roles().probabilities(1)['wolf'],F(1,4))

    def test_changed_evidence_restores_worlds_without_using_parent_weights(self):
        root=BoardData.from_game(game(mediums=1,claims=['medium']+['latent']*4))
        restricted=root.roles()
        self.assertEqual(restricted.probabilities(2)['medium'],0)
        revised=root.updated(claims=['latent']*5)
        restored=revised.roles()
        self.assertEqual(restored.probabilities(2)['medium'],F(1,5))
        self.assertEqual(restored.progress,old_replay(revised.to_game())[1])
        self.assertEqual(restricted.probabilities(2)['medium'],0)

    def test_children_and_current_updates_reconstruct_the_same_evidence(self):
        root=BoardData.from_game(game())
        step=dict(target=5,policy=asdict(Strategy()),claims=['latent']*5,claim_policy={})
        child=root.child(step)
        cold=BoardData.from_game(child.to_game())
        self.assertEqual(child.roles(),cold.roles())
        self.assertEqual(child.roles().progress,old_replay(child.to_game())[1])
        self.assertEqual(root.roles().forecast().village_win,F(7,15))
        self.assertEqual(root.updated(selection=3).roles().rates,root.roles().rates)

    def test_existing_17_lifecycle_cases_match_frozen_reconstruction(self):
        from tests.test_board_owned_log import BoardOwnedLogTests
        from tests.test_public_support_cache import PublicSupportCacheTests
        suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(c)
                                 for c in (BoardOwnedLogTests,PublicSupportCacheTests)])
        baseline=BoardData.roles;calls=[]
        def checked(board):
            result=baseline(board)
            rules,progress=old_replay(board.to_game())
            self.assertEqual(result.rules,rules)
            self.assertEqual(result.progress,progress)
            calls.append(board.facts.slot)
            return result
        with patch.object(BoardData,'roles',checked):
            result=unittest.TestResult();suite.run(result)
        self.assertEqual(result.testsRun,17)
        self.assertTrue(result.wasSuccessful(),result.errors+result.failures)
        self.assertGreater(len(calls),50)
