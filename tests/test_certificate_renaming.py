import unittest
from dataclasses import replace
from fractions import Fraction as F
from tests import test_root_guard_max as fixtures
from tests.test_exact_renaming import rename
from werewolf.seer_manual import replay
from werewolf.exact import Strategy,replace_worlds
from werewolf.root_secret_flow import prepare_root_entry
from werewolf.wolf_profile_certificate import WolfProfileResolver
from werewolf.seer_acquisition import normalize


class CertificateRenamingTests(unittest.TestCase):
    def test_complete_bijection_reuses_only_finished_certificate_and_maps_every_row(self):
        for repeat in (True,False):
            g=fixtures.RootGuardMaxTests().game(repeat,players=5)
            g['policy']['day']=g['history'][0]['policy']['day']='max'
            rules,p=replay(g);strategy=Strategy(**g['policy'])
            root=prepare_root_entry(g,p.board,rules,strategy)
            b,state=root.public,root.public_law
            cached=WolfProfileResolver(rules,strategy)
            original=cached.resolve(b,state)
            self.assertEqual(original.status,'unique')
            bb,ss,past,own=rename(b,state,(),state,1,2)
            before_renamed=cached.certificate_cache_stats['hits']
            actual=cached.resolve(bb,ss,past)
            reference=WolfProfileResolver(rules,strategy,canonical_certificates=False).resolve(bb,ss,past)
            self.assertEqual(actual,reference)
            self.assertEqual(cached.certificate_cache_stats['hits'],before_renamed+1)
            self.assertEqual(sum(len(row) for info,row in actual.selected.scores),
                             sum(len(row) for info,row in original.selected.scores))
            # Complete input masses are part of equality, even if all roles and
            # histories still have the same positive support.
            weighted=replace(ss,hypotheses=normalize(tuple(replace(h,mass=h.mass*(2 if h.roles[0]==1 else 1))
                                                        for h in ss.hypotheses)))
            changed=replace_worlds(bb,weighted.public_roles,wolf_count=None)
            from werewolf.exact_renaming import canonical_key
            changed_key=canonical_key(changed,weighted,(),weighted,None,rules,strategy)
            self.assertNotIn(changed_key,cached.certificate_cache)

    def test_unfinished_certificate_is_not_installed(self):
        g=fixtures.RootGuardMaxTests().game(players=5);rules,p=replay(g);strategy=Strategy(**g['policy'])
        root=prepare_root_entry(g,p.board,rules,strategy)
        resolver=WolfProfileResolver(rules,strategy,max_profiles=1)
        resolver.resolve(root.public,root.public_law)
        self.assertEqual(resolver.certificate_cache,{})
