import unittest
from types import SimpleNamespace
from unittest.mock import patch
from werewolf.navigation_tree import _presentation_source
from werewolf.navigation_history import NameMap
from werewolf.navigation_store import NavigationDocument
from werewolf.public_convergence import transport_source
from werewolf.seer_acquisition import SeerReport
from tests.test_manual_public_input import ManualPublicInputTests

class PublicPresentationProjectionTests(unittest.TestCase):
    def test_public_metadata_matches_complete_transport_without_reading_hidden_laws(self):
        doc=NavigationDocument(ManualPublicInputTests().root().data)
        doc.game.public_input(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),))
        doc.game.action(4)
        source=doc.game.node.read()
        for names in (NameMap((1,2,3,4,5)),NameMap((3,5,1,2,4))):
            expected=transport_source(source,names.forward)
            # Rendering receives no Q/P/physical attributes at all. It cannot
            # accidentally normalize, materialize or inspect their histories.
            public_only=SimpleNamespace(public=source.public,past=source.past)
            node=SimpleNamespace(read=lambda:public_only)
            with patch('werewolf.public_convergence.normalize',side_effect=AssertionError('display normalized a hidden law')):
                shown=_presentation_source(node,names)
            for field in ('alive','claims','history','reports'):
                self.assertEqual(getattr(shown.public,field),getattr(expected.public,field))
            self.assertEqual(shown.past,expected.past)
            self.assertFalse(hasattr(shown,'private'))
            self.assertFalse(hasattr(shown,'public_state'))

    def test_owned_public_projection_never_requests_named_materialization(self):
        # A public-only source also models the admitted anonymous read contract:
        # no reports/private law are needed just to label its public card.
        from werewolf.exact import initial_board
        public=initial_board(5,1,0,1)
        node=SimpleNamespace(read=lambda:SimpleNamespace(public=public))
        shown=_presentation_source(node,NameMap((5,2,3,4,1)))
        self.assertEqual(shown.public.alive,(1,2,3,4,5))
        self.assertEqual(shown.past,())

    def test_equal_mapping_fast_path_keeps_normalized_distribution_fallback(self):
        from dataclasses import replace
        from werewolf.navigation_tree import NavigationTree
        original=ManualPublicInputTests().root().read()
        changed=replace(original,private=replace(original.private,hypotheses=tuple(reversed(original.private.hypotheses))))
        self.assertNotEqual(original.private,changed.private)
        names=NameMap((2,1,3,4,5))
        self.assertEqual(transport_source(original,names.forward),transport_source(changed,names.forward))
        anchor=SimpleNamespace(key='h1',names=names)
        history=SimpleNamespace(occurrence=lambda _:anchor,state=lambda _:SimpleNamespace(source=original),children=lambda _:())
        view=NavigationTree.__new__(NavigationTree)
        view.document=SimpleNamespace(game=SimpleNamespace(history=history))
        tree=SimpleNamespace(nodes={'0':{'node':SimpleNamespace(read=lambda:changed)}})
        view.view=lambda _:(tree,names)
        self.assertEqual(view._binding('h0@h1','0'),'h1')

if __name__=='__main__':unittest.main()

