import unittest
import re
from fractions import Fraction as F
from dataclasses import replace
from app import create_app
from werewolf.exact import (initial_board,group_initial_board,condition_claims,ClaimPolicy,
    co_group_compositions,Rules,Strategy,Progress,advance,build_tree,evaluate_tree,compatible_claim)

NONE=ClaimPolicy(villager='none',medium='none')
def joint(board):return {(w,m):q for w,m,q in board.role_belief}
def explicit(node,strategy):
    if node.board.winner:return F(node.board.winner=='village')
    if node.disclosures:
        values=[sum((c.probability*explicit(c.child,strategy) for c in a.outcomes),F()) for a in node.disclosures]
        return sum(values,F())/len(values) if strategy.fake_reports=='random' else min(values)
    values=[sum((c.probability*explicit(c.child,strategy) for c in a.outcomes),F()) for a in node.actions]
    mode=strategy.day if node.board.phase=='day' else strategy.night
    return sum(values,F())/len(values) if mode=='random' else max(values) if node.board.phase=='day' else min(values)

class GroupModelTests(unittest.TestCase):
    def group(self,k,policy=NONE):
        return group_initial_board(initial_board(9,2,2),('medium',)*k+('latent',)*(9-k),policy)
    def test_approved_coefficients_joint_and_counts(self):
        expected=[{0:F(7,9),1:F(2,9)}, {0:F(7,12),1:F(7,18),2:F(1,36)}, {1:F(6,7),2:F(1,7)}, {2:F(1)}]
        for k,distribution in enumerate(expected,1):
            b=self.group(k);d={}
            for w,m,q in b.role_belief:
                j=(w&((1<<k)-1)).bit_count();d[j]=d.get(j,F())+q
                self.assertTrue(q>0);self.assertEqual(w&m,0)
                self.assertEqual(w.bit_count(),2);self.assertEqual(m.bit_count(),2)
            self.assertEqual(d,distribution)
            self.assertEqual(sum(j*q for j,q in d.items())/k,b.wolf_probability(1))
            self.assertEqual(sum(q for _,_,q in b.role_belief),1)
            for role,count in [('villager',5),('medium',2),('wolf',2)]:self.assertEqual(sum(b.role_probability(i,role) for i in b.alive),count)
            self.assertEqual(sum(q for *_,q in co_group_compositions(b)[0]['compositions']),1)
        self.assertEqual(self.group(2).joint_wolf_probability((1,2)),F(1,36))
        with self.assertRaises(ValueError):self.group(5)
    def test_filled_and_immediate_ccos(self):
        self.assertEqual(self.group(1,ClaimPolicy()).wolf_probability(1),F(2,9))
        for k,q in [(2,F(0)),(3,F(1,3)),(4,F(1,2))]:self.assertEqual(self.group(k,ClaimPolicy()).wolf_probability(1),q)
        with self.assertRaises(ValueError):self.group(1,ClaimPolicy(medium='counter'))
    def test_latent_compatibility_v02_and_multiple_faker_roles(self):
        for n in range(3,10):
            for w in range(1,(n-1)//2+1):
                for m in (0,1,n-w):
                    b=initial_board(n,w,m)
                    self.assertEqual(joint(group_initial_board(b,('latent',)*n)),joint(b))
        settings={'villager':('medium',),'medium':('villager',),'wolf':('villager','medium')}
        b=initial_board(7,2,2);claims=('medium','villager')+('latent',)*5
        a=group_initial_board(b,claims,NONE,settings)
        reverse=group_initial_board(b,claims,NONE,dict(reversed(list(settings.items()))))
        self.assertEqual(joint(a),joint(reverse))
        self.assertEqual(joint(a),joint(condition_claims(b,claims,NONE,settings)))
    def test_mixed_claims_and_position_permutation(self):
        b=initial_board(6,2,1);claims=('wolf','medium','villager','latent','latent','latent')
        a=group_initial_board(b,claims,NONE)
        self.assertEqual(a.wolf_probability(1),1)
        self.assertEqual(a.wolf_probability(2),F(1,5))
        for w,m,q in a.role_belief:self.assertTrue(all(compatible_claim(w,m,i,c) for i,c in enumerate(claims,1)))
        swapped=group_initial_board(b,tuple(reversed(claims)),NONE)
        reverse_mask=lambda mask:sum(1<<(5-i) for i in range(6) if mask&(1<<i))
        self.assertEqual({(reverse_mask(w),reverse_mask(m)):q for w,m,q in a.role_belief},joint(swapped))
        with self.assertRaises(ValueError):group_initial_board(initial_board(5),('medium',)+('latent',)*4)
    def test_conditioning_city_keeps_prior_and_transition_does_not_reseed(self):
        b=self.group(1)
        entries=tuple((w,m,q) for w,m,q in b.role_belief if not (w|m)&2)
        mass=sum(q for _,_,q in entries)
        observed=replace(b,belief=(),role_belief=tuple((w,m,q/mass) for w,m,q in entries))
        self.assertEqual(observed.wolf_probability(1),F(2,9))
        p=advance(Progress(b),2,Rules(),Strategy())
        self.assertEqual(joint(p.board),joint(b))
        self.assertEqual(p.board.wolf_probability(1),F(2,9))
        with self.assertRaises(ValueError):group_initial_board(p.board,p.board.claims,NONE)
    def test_shared_solver_matches_public_full_tree(self):
        b=group_initial_board(initial_board(5,1,1),('medium',)+('latent',)*4,NONE)
        for strategy in (Strategy(),Strategy('random','random'),Strategy(include_self_bite=True)):
            root=build_tree(b,Rules(True),strategy)
            self.assertEqual(evaluate_tree(root,strategy).board_value(root).village_win,explicit(root,strategy))

class GroupWebTests(unittest.TestCase):
    def setUp(self):
        self.c=create_app({'TESTING':True,'SECRET_KEY':'group-test'}).test_client()
        self.c.post('/start',data={'citizens':'5','mediums':'2','wolves':'2','day':'max','night':'max','model':'group','cco_medium':'none'})
    def state(self):
        with self.c.session_transaction() as s:return dict(s['game'])
    def form(self,**changes):
        s=self.state();d={'revision':str(s['revision']),'day':'max','night':'max','cco_medium':s['claim_policy']['medium'],**{f'co_{i+1}':x for i,x in enumerate(s['claims'])}};d.update(changes);return d
    def test_initial_snapshot_order_switch_and_removal(self):
        self.c.post('/strategy',data=self.form(co_1='medium'))
        self.c.post('/strategy',data=self.form(co_2='medium'))
        first=self.c.get('/main').get_data(as_text=True)
        self.c.post('/strategy',data=self.form(co_1='latent',co_2='latent'))
        self.c.post('/strategy',data=self.form(co_2='medium'))
        self.c.post('/strategy',data=self.form(co_1='medium'))
        normalize=lambda html: re.sub(r'"revision": [0-9]+', '"revision": 0', re.sub(r'name="revision" value="[0-9]+"', 'name="revision" value="X"',html))
        self.assertEqual(normalize(first),normalize(self.c.get('/main').get_data(as_text=True)))
        self.assertEqual(self.state()['history'],[])
        before=self.state()
        self.assertEqual(self.c.post('/strategy',data=self.form(model='equal')).status_code,303)
        self.assertEqual(self.state()['model'],'equal')
        self.c.post('/strategy',data=self.form(model='group',co_1='latent',co_2='latent'))
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('data-fraction="5/9"',html)
    def test_normal_group_default_and_legacy_equal_board_preserved(self):
        data={'citizens':'5','mediums':'2','wolves':'2','day':'max','night':'max','cco_medium':'none'}
        self.assertEqual(self.c.post('/start',data=data).status_code,303)
        self.assertEqual(self.state()['model'],'group')
        self.assertEqual(self.c.post('/start',data={**data,'model':'equal'}).status_code,400)
        self.assertEqual(self.state()['model'],'group')
        with self.c.session_transaction() as session:
            state=session['game'];state['model']='equal';session['game']=state
        self.assertEqual(self.c.post('/strategy',data=self.form(co_1='medium')).status_code,303)
        self.assertEqual(self.state()['model'],'equal')
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('name="model" value="equal"',html)
        self.assertIn('data-fraction="1/2"',html)
        before=self.state()
        self.assertEqual(self.c.post('/strategy',data=self.form(model='group')).status_code,303)
        self.assertEqual(self.state()['model'],'group')

    def test_phase_history_weight_back_and_later_edit(self):
        self.c.post('/strategy',data=self.form(co_1='medium',target='2'))
        self.c.post('/advance',data=self.form(target='2'))
        state=self.state();self.assertEqual(len(state['history']),1)
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('data-fraction="2/9"',html)
        self.assertEqual(self.c.post('/strategy',data=self.form(model='equal')).status_code,400)
        self.assertEqual(self.state(),state)
        self.c.post('/strategy',data=self.form(co_3='medium'))
        self.assertEqual(self.state()['history'],state['history'])
        self.c.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertEqual(self.state()['claims'],['medium']+['latent']*8)
        self.assertEqual(self.state()['selection'],2)
        self.assertEqual(self.state()['model'],'group')
    def test_comparison_joint_model_preserves_game(self):
        before=self.state()
        html=self.c.post('/comparison',data={'citizens':'5','mediums':'2','wolves':'2','cco_medium':'none','co_1':'medium','co_2':'medium','mode':'group'}).get_data(as_text=True)
        self.assertIn('data-fraction="1/36"',html)
        self.assertIn('COグループ方式の村勝率',html)
        self.assertEqual(self.state(),before)

if __name__=='__main__':unittest.main()
