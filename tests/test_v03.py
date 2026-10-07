import unittest
from fractions import Fraction as F
from itertools import product
from werewolf.exact import (ClaimPolicy, Rules, Strategy, Progress, Board, initial_board,
 condition_claims, action_outcomes, advance, legal_targets, build_tree, evaluate_tree)
from app import create_app


def value(board, strategy=Strategy(), rules=Rules()):
    node=build_tree(board,rules,strategy)
    return evaluate_tree(node,strategy).board_value(node).village_win


def explicit_value(node, strategy):
    if node.board.winner: return F(node.board.winner=='village')
    if node.disclosures:
        candidates=[sum((chance.probability*explicit_value(chance.child,strategy) for chance in a.outcomes),F(0)) for a in node.disclosures]
        return sum(candidates,F(0))/len(candidates) if strategy.fake_reports=='random' else min(candidates)
    candidates=[sum((chance.probability*explicit_value(chance.child,strategy) for chance in a.outcomes),F(0)) for a in node.actions]
    mode=strategy.day if node.board.phase=='day' else strategy.night
    return sum(candidates,F(0))/len(candidates) if mode=='random' else max(candidates) if node.board.phase=='day' else min(candidates)


class ClaimTests(unittest.TestCase):
    def test_all_hidden_and_zero_medium_v02_values(self):
        for n in range(3,10):
            for w in range(1,(n-1)//2+1):
                for m in (0,1,n-w):
                    b=initial_board(n,w,m)
                    self.assertEqual(sum(b.role_probability(i,'medium') for i in b.alive),m)
                    self.assertEqual(sum(b.role_probability(i,'wolf') for i in b.alive),w)
                    self.assertEqual(sum(b.role_probability(i,'villager') for i in b.alive),n-m-w)
                    for i in b.alive:
                        self.assertEqual(b.role_probability(i,'medium'),F(m,n))
                        self.assertEqual(sum(b.role_probability(i,r) for r in ('villager','medium','wolf')),1)
                    self.assertEqual(value(b),value(initial_board(n,w)))

    def test_one_claim_default_counter_and_no_counter(self):
        claims=('medium',)+('latent',)*4
        b=condition_claims(initial_board(5,1,1),claims)
        self.assertEqual(b.role_probability(1,'medium'),1)
        self.assertEqual(b.role_probability(2,'wolf'),F(1,4))
        self.assertEqual(value(b),F(1,2))
        e=evaluate_tree(build_tree(b,Rules(),Strategy()),Strategy())
        self.assertEqual(e.action_value(build_tree(b,Rules(),Strategy()),1).village_win,F(1,3))
        b=condition_claims(initial_board(5,1,1),claims,ClaimPolicy(medium='none'))
        self.assertEqual(b.role_probability(1,'medium'),F(1,2))
        self.assertEqual(b.role_probability(1,'wolf'),F(1,2))
        self.assertEqual(b.role_probability(2,'medium'),F(1,8))
        self.assertEqual(b.role_probability(2,'wolf'),F(1,8))
        self.assertEqual(value(b),F(2,3))

    def test_two_claims_correlations_and_public_strategy(self):
        b=condition_claims(initial_board(5,1,1),('medium','medium','latent','latent','latent'))
        self.assertEqual(b.role_probability(1,'medium'),F(1,2))
        self.assertEqual(b.role_probability(2,'wolf'),F(1,2))
        self.assertEqual(b.joint_wolf_probability((1,2)),0)
        self.assertEqual(b.role_probability(3,'villager'),1)
        self.assertEqual(value(b),1)
        self.assertEqual(value(b,Strategy('random','max')),F(7,15))
        for strategy in (Strategy(),Strategy('random','random'),Strategy(include_self_bite=True)):
            rules=Rules(True);root=build_tree(b,rules,strategy)
            self.assertEqual(evaluate_tree(root,strategy).board_value(root).village_win, explicit_value(root,strategy))

    def test_filled_default_capacity_and_immediate_counter(self):
        self.assertEqual(ClaimPolicy().medium, 'filled')
        b = initial_board(6, 1, 2)
        one = ('medium',) + ('latent',) * 5
        c = condition_claims(b, one)
        self.assertEqual(c.role_probability(1, 'medium'), F(2, 3))
        self.assertEqual(c.role_probability(2, 'medium'), F(4, 15))
        self.assertEqual(c.role_probability(2, 'wolf'), F(2, 15))
        self.assertEqual(sum(q for _, _, q in c.role_belief), 1)
        self.assertEqual(c.role_belief, condition_claims(b, one, ClaimPolicy(medium='none')).role_belief)
        with self.assertRaises(ValueError): condition_claims(b, one, ClaimPolicy(medium='counter'))
        for count in (2, 3):
            claims = ('medium',) * count + ('latent',) * (6-count)
            filled = condition_claims(b, claims)
            immediate = condition_claims(b, claims, ClaimPolicy(medium='counter'))
            self.assertEqual(filled.role_belief, immediate.role_belief)
            self.assertEqual(filled.role_probability(count+1, 'medium'), 0)
        with self.assertRaises(ValueError): condition_claims(b, ('medium',)*4+('latent',)*2)
        for count in (1,2):
            claims = ('medium',)*count + ('latent',)*(5-count)
            self.assertEqual(condition_claims(initial_board(5,1,1),claims).role_belief,
                             condition_claims(initial_board(5,1,1),claims,ClaimPolicy(medium='counter')).role_belief)

    def test_multiple_mediums_unrestricted_counts_and_ccos(self):
        b=initial_board(6,1,2)
        with self.assertRaises(ValueError): condition_claims(b,('medium',)+('latent',)*5,ClaimPolicy(medium='counter'))
        c=condition_claims(b,('medium','medium')+('latent',)*4)
        self.assertEqual(c.role_probability(1,'medium'),1)
        self.assertEqual(c.role_probability(3,'wolf'),F(1,4))
        c=condition_claims(b,('medium','medium','medium')+('latent',)*3)
        self.assertEqual(c.role_probability(1,'medium'),F(2,3))
        self.assertEqual(c.role_probability(1,'wolf'),F(1,3))
        self.assertEqual(c.joint_wolf_probability((1,2)),0)
        c=condition_claims(b,('medium',)+('latent',)*5,ClaimPolicy(medium='none'))
        self.assertGreater(c.role_probability(2,'medium'),0)
        self.assertEqual(initial_board(9,1,8).initial_medium_count,8)

    def test_impossible_claim_count_and_role_constraint(self):
        with self.assertRaises(ValueError): condition_claims(initial_board(5,1,1),('medium','medium','medium','latent','latent'))
        with self.assertRaises(ValueError): condition_claims(initial_board(5),('medium',)+('latent',)*4)
        # Wolves can claim a role; the user can submit the claim without the UI
        # knowing its true author. Joint consistency determines its support.
        b=condition_claims(initial_board(5,1,1),('wolf',)+('latent',)*4)
        self.assertEqual(b.role_probability(1,'wolf'),1)
        p=advance(Progress(b),2,Rules(),Strategy())
        self.assertNotIn(1,legal_targets(p.board,Rules(),Strategy()))
        with self.assertRaises(ValueError): action_outcomes(p.board,1,Rules(),Strategy())
        self.assertIn(1,legal_targets(p.board,Rules(True),Strategy(include_self_bite=True)))

    def test_co_history_and_no_new_ability_information(self):
        b=condition_claims(initial_board(7,2,2),('medium','medium')+('latent',)*5)
        p=advance(Progress(b),3,Rules(),Strategy())
        self.assertEqual(p.board.claims,b.claims)
        before=p.board.wolf_count_distribution
        p=advance(p,4,Rules(),Strategy())
        self.assertEqual(p.board.wolf_count_distribution,before)
        self.assertEqual(p.board.claims,b.claims)
        self.assertFalse(hasattr(p.board,'medium_results'))

    def test_all_small_claim_patterns_have_exact_mass_or_conflict(self):
        base=initial_board(5,1,1)
        for claims in product(('latent','medium','wolf'),repeat=5):
            for policy in (ClaimPolicy(),ClaimPolicy(medium='none')):
                try: b=condition_claims(base,claims,policy)
                except ValueError: continue
                self.assertEqual(sum(q for _,_,q in b.role_belief),1)
                self.assertTrue(all(w&m==0 and m.bit_count()==1 and w.bit_count()==1 for w,m,q in b.role_belief))
                self.assertTrue(0 <= value(b) <= 1)


class ClaimWebTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'test'});self.c=self.app.test_client()
    def state(self):
        with self.c.session_transaction() as session:return session.get('game')
    def form(self,**changes):
        s=self.state();d={'revision':str(s['revision']),'day':s['policy']['day'],'night':s['policy']['night'],'cco_villager':s['claim_policy']['villager'],'cco_medium':s['claim_policy']['medium']}
        d.update({f'co_{i+1}':x for i,x in enumerate(s['claims'])});d.update(changes);return d
    def start(self,citizens=3,mediums=1,wolves=1):
        return self.c.post('/start',data={'citizens':str(citizens),'mediums':str(mediums),'wolves':str(wolves),'day':'max','night':'max'})
    def test_top_role_counts_and_fixed_calculation_options(self):
        html=self.c.get('/').get_data(as_text=True)
        for text in ('村陣営','狼陣営','市民','霊能','騙れる役職','CO必須','対抗が出たらCCO','自動吊り先','自動噛み先'):
            self.assertIn(text,html)
        self.assertEqual(self.start(0,8,1).status_code,303)
        self.assertEqual(self.state()['players'],9)
        for c,m,w in [(0,1,1),(4,4,2),(3,-1,1),(3,1,0),(1,1,2)]:
            self.assertEqual(self.start(c,m,w).status_code,400)
    def test_filled_top_default_and_current_phase_condition_changes(self):
        self.start(citizens=3,mediums=2)
        self.assertEqual(self.state()['claim_policy'], {'villager':'filled','medium':'filled','wolf':'none'})
        top = self.c.get('/').get_data(as_text=True)
        self.assertEqual(top.count('value="filled" checked'),4)
        self.assertEqual(self.c.post('/strategy',data=self.form(co_1='medium',target='4')).status_code,303)
        self.assertEqual(self.state()['history'],[])
        self.assertEqual(self.state()['selection'],4)
        before=self.state()
        self.assertEqual(self.c.post('/strategy',data=self.form(cco_medium='counter')).status_code,400)
        self.assertEqual(self.state(),before)
        self.assertEqual(self.c.post('/strategy',data=self.form(co_2='medium')).status_code,303)
        self.assertEqual(self.c.post('/strategy',data=self.form(cco_medium='counter')).status_code,303)
        self.assertEqual(self.c.post('/strategy',data=self.form(cco_medium='filled')).status_code,303)
        self.assertEqual(self.state()['history'],[])

    def test_co_changes_probability_and_comparing_ccos(self):
        self.start()
        # Preserve the original uniform-model regression as a saved legacy Board.
        with self.c.session_transaction() as session:
            state = dict(session['game']); state['model'] = 'equal'; session['game'] = state
        self.assertEqual(self.c.post('/strategy',data=self.form(co_1='medium')).status_code,303)
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('<th>CO</th>',html);self.assertIn('id="village-rate" class="probability" data-fraction="1/2"',html)
        self.assertEqual(self.c.post('/strategy',data=self.form(cco_medium='none')).status_code,303)
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('id="village-rate" class="probability" data-fraction="2/3"',html)
        self.assertEqual(self.state()['history'],[])
        self.assertEqual(self.c.post('/strategy',data=self.form(co_1='latent')).status_code,303)
        self.assertIn('id="village-rate" class="probability" data-fraction="7/15"',self.c.get('/main').get_data(as_text=True))
    def test_conflicting_co_does_not_mutate_state(self):
        self.start();before=self.state()
        response=self.c.post('/strategy',data=self.form(co_1='medium',co_2='medium',co_3='medium'))
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.state(),before)
        self.assertIn('CCO',response.get_data(as_text=True))
    def test_back_restores_claims_and_conditions_and_new_targets(self):
        self.start();self.c.post('/strategy',data=self.form(co_1='medium',cco_medium='none'))
        self.assertEqual(self.c.post('/advance',data=self.form(target='2')).status_code,303)
        history=self.state()['history']
        self.c.post('/strategy',data=self.form(co_3='medium',cco_medium='counter'))
        self.assertEqual(self.state()['history'],history)
        self.assertEqual(self.c.post('/back',data={'revision':str(self.state()['revision'])}).status_code,303)
        self.assertEqual(self.state()['claims'],['medium','latent','latent','latent','latent'])
        self.assertEqual(self.state()['claim_policy']['medium'],'none')
        self.assertEqual(self.state()['selection'],2)
    def test_stale_claim_apply_and_result_injection_rejected(self):
        self.start();data=self.form(co_1='medium')
        self.assertEqual(self.c.post('/strategy',data=data).status_code,303)
        self.assertEqual(self.c.post('/strategy',data=data).status_code,409)
        self.assertEqual(self.c.post('/strategy',data=self.form(medium_result='black')).status_code,400)
