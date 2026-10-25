"""Two linked seer claims and a medium: actual persistent night merge regression."""
import json,unittest
from pathlib import Path
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree

class CountJointTreeTests(unittest.TestCase):
    def test_two_co_night_projection_and_cold_history_preserve_exact_sources(self):
        saved=json.loads((Path(__file__).parent/'fixtures/count_joint_two_co.json').read_text())
        document=NavigationDocument.restore(saved)
        before=document.export()
        tree=NavigationTree(document)
        tree.read('h1~0',True,compact=True)
        # The reported failure is the first nonterminal post-execution branch.
        tree.read('h1~3',True,compact=True)
        tree.read('h2~0',True,compact=True)
        self.assertEqual(document.export(),before)
        self.assertEqual(document.game.history.state('h2').node.read().public.alive,(1,2,3,5,6,7))
        for view,names in tree.views.values():
            for record in view.nodes.values():
                source=record['node'].read()
                self.assertEqual(source.physical.worlds,source.private.public_roles)
                self.assertEqual(sum(source.physical.wolf_count_distribution.values()),1)
