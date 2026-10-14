import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import initial_board,condition_claims,ClaimPolicy,Rules,Strategy,replace_worlds
from werewolf.seer_acquisition import from_board,normalize,SeerReport
from werewolf.seer_future_uniform import TrueScanState
from werewolf.actor_information import WolfInformation
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.exact_renaming import canonical_key
from werewolf.guard_model import condition_guard_observation,public_guard_branch_law,GuardObserver
import werewolf.model_a_public as public


def rename(b,s,past,private,x,y):
    def p(i):return y if i==x else x if i==y else i
    def mask(m):return sum(1<<(p(i)-1) for i in range(1,b.player_count+1) if m&(1<<(i-1)))
    def rec(r):return replace(r,**{k:p(getattr(r,k)) for k in ('player','reporter','actor','target') if hasattr(r,k)})
    def law(st):return replace(st,hypotheses=normalize(tuple(replace(h,roles=tuple(mask(m) for m in h.roles),acquisitions=tuple(sorted(rec(a) for a in h.acquisitions)),guards=tuple(rec(g) for g in h.guards),attacks=tuple(rec(a) for a in h.attacks)) for h in st.hypotheses)),rosters=tuple(tuple(sorted(p(i) for i in r)) for r in st.rosters),tracked=None if st.tracked is None else tuple(sorted(p(i) for i in st.tracked)))
    claims=['']*b.player_count
    for i,c in enumerate(b.claims,1):claims[p(i)-1]=c
    bb=replace_worlds(b,tuple((*tuple(mask(m) for m in w[:-1]),w[-1]) for w in b.worlds),alive=tuple(sorted(p(i) for i in b.alive)),claims=tuple(claims),history=tuple(rec(r) for r in b.history),medium_opportunities=tuple(sorted((d,p(a),p(t)) for d,a,t in b.medium_opportunities)),reports=tuple(rec(r) for r in b.reports),report_resolved=tuple(sorted((d,p(a),p(t)) for d,a,t in b.report_resolved)),guard_prior_roster=None if b.guard_prior_roster is None else (b.guard_prior_roster[0],tuple(sorted(p(i) for i in b.guard_prior_roster[1]))))
    return bb,law(s),tuple(rec(r) for r in past),law(private)

class ExactRenamingTests(unittest.TestCase):
    def fixture(self):
        b=condition_claims(initial_board(5,1,0,0,1),('hunter','latent','latent','latent','latent'),ClaimPolicy())
        s=TrueScanState(from_board(b),rosters=(b.alive,))
        return b,s

    def key(self,b,s,past=(),private=None,target=None,repeat=True,observer=None):
        return canonical_key(b,s,past,s if private is None else private,observer,Rules(allow_repeat_guard=repeat),Strategy(),target=target)

    def test_whole_state_bijection_and_actor_partition(self):
        b,s=self.fixture();own=WolfInformation(2).condition_public(s)
        original=self.key(b,s,private=own,target=3)
        bb,ss,past,private=rename(b,s,(),own,2,4)
        self.assertEqual(original,self.key(bb,ss,past,private,target=3))
        self.assertNotEqual(original,self.key(b,s,private=own,target=2))
        self.assertNotEqual(original,self.key(b,s,private=own,target=3,repeat=False))
        self.assertEqual(self.key(b,s,target=2),self.key(b,s,target=3))

    def test_asymmetric_weights_and_directed_private_attack_history(self):
        b,s=self.fixture();worlds=tuple((*w[:-1],F(2,5) if w[0]==2 else F(1,5)) for w in b.worlds)
        weighted=replace_worlds(b,worlds);law=TrueScanState(from_board(weighted),rosters=s.rosters)
        self.assertNotEqual(self.key(weighted,law,target=2),self.key(weighted,law,target=3))
        b=replace(b,phase='night');e=InformationSetForecast(Rules(),Strategy(day='random',night='random'))
        acquired=e.acquire(b,s);child=replace(condition_guard_observation(b,(),e.rules,state=acquired),day=2,phase='day')
        child,law=public_guard_branch_law(b,acquired,child,None,True,e)
        from werewolf.night_knowledge import WolfAttack
        own=WolfInformation(2,(WolfAttack(1,3),)).condition_public(law)
        self.assertNotEqual(self.key(child,law,private=own,target=3),self.key(child,law,private=own,target=4))
        bb,ss,past,private=rename(child,law,(),own,3,4)
        self.assertEqual(self.key(child,law,private=own,target=3),self.key(bb,ss,past,private,target=4))

    def test_seer_acquisition_and_public_report_edges_are_preserved(self):
        from werewolf.seer_future_uniform import acquire_uniform
        b=condition_claims(initial_board(5,1,0,1,1),('hunter','seer','latent','latent','latent'),ClaimPolicy())
        s=acquire_uniform(TrueScanState(from_board(b)),b.alive)
        from werewolf.actor_information import condition_actor_state
        s=condition_actor_state(s,lambda h:any(a.day==1 and a.player==2 and a.target==3 and a.color=='white' for a in h.acquisitions))
        b=replace_worlds(b,s.public_roles)
        past=(SeerReport(1,1,2,3,'white'),)
        bb,ss,pp,own=rename(b,s,past,s,3,4)
        self.assertEqual(self.key(b,s,past,target=3),self.key(bb,ss,pp,own,target=4))
        self.assertNotEqual(self.key(b,s,past,target=3),self.key(b,s,past,target=4))
        # A partial player-only rename cannot merge directed scan/report edges.
        self.assertNotEqual(self.key(b,s,past,target=3),self.key(bb,ss,past,own,target=4))
        self.assertIsNone(self.key(b,s,observer=lambda h,st:True))

    def test_guard_owner_intervention_is_not_an_oracle_or_public_key(self):
        b,s=self.fixture()
        observer=GuardObserver(b,1,2,tuple(w[:-1] for w in b.worlds))
        first=self.key(b,s,observer=observer,target=2)
        self.assertIsNotNone(first)
        self.assertNotEqual(first,self.key(b,s,target=2))
        self.assertNotEqual(first,self.key(b,s,observer=observer,target=3))
        self.assertIsNone(canonical_key(b,s,(),s,None,Rules(),Strategy(),max_mappings=1))

    def test_full_forecast_and_tie_rows_match_with_compression_disabled(self):
        b,s=self.fixture()
        for repeat in (True,False):
            results=[];engines=[]
            for compressed in (False,True):
                class Capture(InformationSetForecast):
                    def __init__(self,*a,**kw):super().__init__(*a,**kw,exact_renaming=compressed);engines.append(self)
                with patch.object(public,'InformationSetForecast',Capture):
                    result=public.public_forecast(b,s,(),Rules(allow_repeat_guard=repeat),Strategy(day='random',night='random'),max_seconds=20)
                self.assertFalse(hasattr(result,'reason'),result)
                results.append(result)
            self.assertEqual(results[0],results[1])
            self.assertGreater(engines[1].renaming_stats['supported'],0)
            self.assertLess(engines[1].expansions['actions'],engines[0].expansions['actions'])
            self.assertEqual(len(results[1].action_values),5)

    def test_max_policies_and_private_wolf_laws_match_without_compression(self):
        b=condition_claims(initial_board(5,2,0,0,1),('hunter',)+('latent',)*4,ClaimPolicy())
        s=TrueScanState(from_board(b),rosters=(b.alive,))
        results=[];private_values=[]
        for compressed in (False,True):
            class Capture(InformationSetForecast):
                def __init__(self,*a,**kw):super().__init__(*a,**kw,exact_renaming=compressed)
            with patch.object(public,'InformationSetForecast',Capture):
                result=public.public_forecast(b,s,(),Rules(),Strategy(),max_seconds=20)
            self.assertFalse(hasattr(result,'reason'),result)
            results.append(result)
            e=Capture(Rules(),Strategy())
            private_values.append(tuple(e.solve(b,s,(),WolfInformation(mask).condition_public(s),None)
                                        for mask in (6,10)))
            with patch.object(public,'InformationSetForecast',Capture):
                unsupported=public.public_forecast(b,s,(),Rules(allow_repeat_guard=False),Strategy(),max_seconds=20)
            self.assertEqual(unsupported.reason,'guard_no_repeat_max_unimplemented')
        self.assertEqual(results[0],results[1])
        self.assertEqual(private_values[0],private_values[1])
