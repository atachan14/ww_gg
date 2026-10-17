import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.run import source
from werewolf.matching_comparison import ComparisonContext,PublicRelations
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.seer_acquisition import normalize,SeerReport
from werewolf.exact import replace_worlds


class MatchingComparisonTests(unittest.TestCase):
    def setUp(self):
        _,_,b,s,past,rules,strategy,view=source(5,1)
        self.relations=PublicRelations.from_view(view)
        self.context=ComparisonContext(rules,strategy,self.relations)
        self.payload=ContinuationInputs(b,s,past,s,None,b)

    def test_hidden_joint_physical_history_and_configuration_cannot_alias(self):
        c=self.context;p=self.payload
        original=c.certify(p)
        self.assertIsNotNone(original)
        # Keep the exact same public Player rows and public law, changing only
        # private joint weights or actual branch mass. Neither may be ignored.
        private=replace(p.private,hypotheses=normalize(tuple(replace(h,mass=h.mass*(2 if h.roles[0]==2 else 1))for h in p.private.hypotheses)))
        physical=replace_worlds(p.physical,tuple((*h.roles,h.mass)for h in private.hypotheses))
        changes=(replace(p,private=private),replace(p,physical=physical),
                 replace(p,past=(SeerReport(1,1,1,2,'white'),)))
        for changed in changes:
            self.assertNotEqual(original.key,c.certify(changed).key)
        self.assertNotEqual(original.key,replace(c,rules=replace(c.rules,allow_repeat_guard=False)).certify(p).key)
        self.assertNotEqual(original.key,replace(c,strategy=replace(c.strategy,day='max')).certify(p).key)
        self.assertIsNone(c.certify(replace(p,observer=lambda h,s:True)))

    def test_snapshot_references_and_public_relation_updates(self):
        c=self.context;p=self.payload
        self.assertIs(p.public_state,p.private)
        self.assertIs(p.public,p.physical)
        self.assertIs(c.relations,self.relations)
        before=c.certify(p)
        updated=replace(c,relations=replace(c.relations,claims=('latent',)*5))
        self.assertNotEqual(before.key,updated.certify(p).key)
        self.assertEqual(before,c.certify(p))
        # A request context is a reference carrier, not itself an equality key.
        self.assertNotEqual(c,replace(c))
        self.assertEqual(before,replace(c).certify(p))

    def test_search_cap_still_fails_closed(self):
        _,_,b,s,past,rules,strategy,view=source(7,1)
        c=ComparisonContext(rules,strategy,PublicRelations.from_view(view))
        self.assertIsNone(c.certify(ContinuationInputs(b,s,past,s,None,b)))
