import unittest,tempfile
from fractions import Fraction as F
from unittest.mock import patch
from pathlib import Path
from benchmarks.player_match_groups import checkpoint_audit as base
from benchmarks.player_match_groups import primitive_checkpoint as primitive


class PrimitiveCheckpointTests(unittest.TestCase):
    def test_selector_retains_whole_information_group_and_original_weight(self):
        group=object();other=object();metadata=object()
        term={'bite':3,'signature':'full-joint-signature','weight':F(1,7),'inputs':group}
        terms=[{'bite':3,'signature':'other','weight':F(2,7),'inputs':other},term]
        def planner(*args):return terms,metadata
        def worker(*args):
            selected,actual_metadata=base.night_plan(None,None,1)
            self.assertEqual(len(selected),1)
            self.assertIs(selected[0],term);self.assertIs(selected[0]['inputs'],group)
            self.assertEqual(selected[0]['weight'],F(1,7))
            self.assertIs(actual_metadata,metadata)
            return 'original-worker-called'
        with patch.object(base,'night_plan',planner),patch.object(base,'worker',worker):
            result=primitive.selected_worker(Path('unused'),{'root':1,'bite':3,'index':1,'signature':'full-joint-signature','weight':'1/7'},'oracle',Path('unused'),1,1500000000,base.engine_version(),primitive.adapter_version())
            self.assertEqual(result,'original-worker-called')
            self.assertIs(base.night_plan,planner)

    def test_selector_rejects_changed_conditioning_signature(self):
        def planner(*args):return [{'bite':3,'signature':'different','weight':F(1)}],{}
        def worker(*args):return base.night_plan(None,None,1)
        with patch.object(base,'night_plan',planner),patch.object(base,'worker',worker):
            with self.assertRaisesRegex(ValueError,'primitive plan changed'):
                primitive.selected_worker(Path('unused'),{'root':1,'bite':3,'index':0,'signature':'expected','weight':'1'},'oracle',Path('unused'),1,1500000000,base.engine_version(),primitive.adapter_version())

    def test_committed_input_and_partial_results_restore_without_recomputation(self):
        with tempfile.TemporaryDirectory(prefix='ww-primitive-provenance-')as folder:
            with patch.object(base,'CACHE',Path(folder)):
                path,game,plans,items=primitive.context(7,2)
                parts,imports=primitive.import_legacy(7,2,game,plans,items,base.engine_version(),primitive.adapter_version())
                self.assertEqual(imports['complete_unit_pairs'],14)
                self.assertEqual(imports['verified_prefix_terms'],3)
                self.assertEqual((len(parts['oracle']),len(parts['audit'])),(86,83))
                with self.assertRaisesRegex(ValueError,'Legacy engine/input mismatch'):
                    primitive.import_legacy(7,2,game,plans,items,'changed-core',primitive.adapter_version())
