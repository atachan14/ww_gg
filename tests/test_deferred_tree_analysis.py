import unittest
from unittest.mock import patch
from werewolf.calculation_tree import CalculationTree
from tests import test_anonymous_night as native_tests

class DeferredTreeAnalysisTests(unittest.TestCase):
    def tree(self):
        calculation,node=native_tests.AnonymousNightTests().case()
        calculation._ClosedCalculation__engine.anonymous_nights=True
        return CalculationTree.from_node(node)

    def composition(self,tree,key):
        return any(isinstance(step,dict) and step.get('physical')=='composition' for step in tree.nodes[key]['route'])

    def test_native_public_response_does_not_evaluate_unopened_compositions(self):
        tree=self.tree();value=tree.value
        def public_only(key):
            if self.composition(tree,key):raise AssertionError('unopened composition evaluated')
            return value(key)
        with patch.object(tree,'value',side_effect=public_only):
            deferred=tree.read(tree.root,True,compact=True,defer_analysis=True)
        full=tree.read(tree.root,False,compact=True)
        self.assertEqual(deferred['village_win'],full['village_win'])
        self.assertEqual(deferred['night_stages'],full['night_stages'])
        self.assertEqual(deferred['compositions'],full['compositions'])
        self.assertTrue(set(full['items'])-set(deferred['items']))
        for key,row in deferred['items'].items():self.assertEqual(row,full['items'][key])
        for key in set(full['items'])-set(deferred['items']):self.assertTrue(self.composition(tree,key))
        # Explicit analysis still computes the conditional values, without
        # substituting the public parent's value for a missing composition.
        distribution=tree.distribution(tree.root)
        self.assertEqual({row['probability'] for row in distribution},{'1/4','3/4'})
        # Four live players, one wolf, uniform hidden play: after the safe bite,
        # the next execution hits the wolf with probability1/3, in either
        # seer-survival composition.
        self.assertEqual({row['village_win'] for row in distribution},{'1/3'})
        self.assertEqual([row['probability'] for row in distribution],
                         [part['probability'] for part in deferred['compositions']])

    def test_opt_in_does_not_change_legacy_non_native_composition_flow(self):
        tree=self.tree();tree.engine.anonymous_nights=False
        first=tree.read(tree.root,False,compact=True,defer_analysis=True)
        second=tree.read(tree.root,False,compact=True)
        self.assertEqual(first,second)

    def test_http_deferred_is_opt_in_and_analysis_remains_exact(self):
        import tempfile
        from app import create_app
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(dict(TESTING=True,SECRET_KEY='deferred-test',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
            client=app.test_client()
            client.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
            revision=client.get('/navigation').json['revision']
            result=client.post('/navigation/advance',json=dict(revision=revision,target=1))
            self.assertEqual(result.status_code,200)
            original=CalculationTree.value
            def guarded(tree,key):
                if self.composition(tree,key):raise AssertionError('unopened HTTP composition evaluated')
                return original(tree,key)
            with patch.object(CalculationTree,'value',new=guarded):
                deferred=client.get('/game-tree?node=h1~0&expand=1&format=public-tree&defer_analysis=1')
            self.assertEqual(deferred.status_code,200)
            full=client.get('/game-tree?node=h1~0&format=public-tree')
            self.assertEqual(full.status_code,200)
            self.assertEqual(deferred.json['village_win'],full.json['village_win'])
            self.assertEqual(deferred.json['night_stages'],full.json['night_stages'])
            analysis=client.get('/game-tree?node=h1~0&format=public-tree&defer_analysis=1&analysis=1')
            self.assertEqual(analysis.status_code,200)
            self.assertIn('distribution',analysis.json)

    def test_opened_analysis_does_not_solve_other_future_compositions(self):
        from werewolf.navigation_store import NavigationDocument
        from werewolf.navigation_tree import NavigationTree
        from tests.test_manual_public_input import ManualPublicInputTests
        doc=NavigationDocument(ManualPublicInputTests().root().data)
        doc.game.action(1)
        view=NavigationTree(doc);owner=doc.game.current;tree,names=view.view(owner)
        tree.engine.anonymous_nights=True
        view.read(owner+'~0',True,compact=True,defer_analysis=True)
        allowed={part['node'] for part in tree._composition_rows(tree.root)}
        original=tree.value
        def requested_only(key):
            if self.composition(tree,key) and key not in allowed:raise AssertionError('unopened future analysis evaluated')
            return original(key)
        with patch.object(tree,'value',side_effect=requested_only):
            shown=view.read(owner+'~0',False,analysis=True,compact=True,defer_analysis=True)
        self.assertEqual({row['village_win'] for row in shown['distribution']},{'1/3'})
