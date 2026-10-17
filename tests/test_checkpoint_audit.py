import copy,json,tempfile,unittest
from pathlib import Path
from benchmarks.player_match_groups import checkpoint_audit as checkpoints
from benchmarks.player_match_groups.initial_white import initial_white_source


class CheckpointAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game=initial_white_source(5,1,actors=(1,2))[0].to_game()

    def test_missing_interventions_are_pending_not_zero(self):
        part={'1':{'status':'complete','action':'1/2','dawn':{'village_win':'0','wolf_win':'0'}}}
        result=checkpoints.aggregate(self.game,part)
        self.assertEqual(result['status'],'pending')
        self.assertIsNone(result['value']);self.assertIsNone(result['table'])
        self.assertEqual(result['completed_targets'],[1])

    def test_max_is_rejected_instead_of_replaced_by_uniform(self):
        game=copy.deepcopy(self.game);game['policy']['day']='max'
        with self.assertRaisesRegex(ValueError,'max is not repartitioned'):
            checkpoints.prepared_game(game)

    def test_memory_limit_preserves_only_completed_horizon(self):
        with tempfile.TemporaryDirectory(prefix='ww-checkpoint-memory-')as folder:
            root=Path(folder);case=root/'input.json';output=root/'result.json'
            checkpoints.write(case,self.game)
            row=checkpoints.worker(case,3,'oracle',output,10,1,checkpoints.engine_version(),1)
            self.assertEqual(row['status'],'pending');self.assertEqual(row['reason'],'memory_limit')
            self.assertIsNone(row['action']);self.assertIsNotNone(row['dawn'])

    def test_stale_engine_version_cannot_publish_a_complete_result(self):
        with tempfile.TemporaryDirectory(prefix='ww-checkpoint-version-')as folder:
            root=Path(folder);case=root/'input.json';output=root/'result.json'
            checkpoints.write(case,self.game)
            row=checkpoints.worker(case,3,'oracle',output,10,1500000000,'stale-engine',1)
            self.assertEqual(row['status'],'pending');self.assertIsNone(row['action'])
            self.assertIn('Engine fingerprint changed',row['reason'])
