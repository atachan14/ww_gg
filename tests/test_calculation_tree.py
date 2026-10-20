import unittest
from fractions import Fraction as F
from functools import lru_cache
from unittest.mock import patch
from app import create_app

@lru_cache(None)
def independent(alive,worlds,phase):
    """Enumerate concrete one-wolf placements and every configured tied action.

    No production recurrence, Board transition, forecast or cache is called.
    Uniform no-information placements make all public targets and every wolf's
    legal victims permutation-equivalent; MAX ties use uniform distributions.
    """
    if not worlds:return F(1)
    if len(alive)<=2:return F()
    total=F()
    if phase=='day':
        for target in alive:
            hit=sum(q for wolf,q in worlds if wolf==target)
            kept=tuple((w,q/(1-hit)) for w,q in worlds if w!=target) if hit<1 else ()
            total+=(hit+(1-hit)*independent(tuple(p for p in alive if p!=target),kept,'night'))/len(alive)
    else:
        for target in alive:
            chance=sum(q/F(len(alive)-1) for wolf,q in worlds if wolf!=target)
            if not chance:continue
            kept=tuple((w,q/F(len(alive)-1)/chance) for w,q in worlds if w!=target)
            total+=chance*independent(tuple(p for p in alive if p!=target),kept,'day')
    return total

class CalculationTreeTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'tree-tests','GAME_TREE_PREVIEW':True})
        self.c=self.app.test_client();self.c.post('/start',data={'players':'5','day':'max','night':'max'})
    def test_real_root_lazy_Boards_to_terminal_match_independent_enumeration(self):
        expected=independent((1,2,3,4,5),tuple((p,F(1,5)) for p in range(1,6)),'day')
        self.assertEqual(expected,F(7,15));page=self.c.get('/main');self.assertIn(b'data-calculation-tree',page.data)
        root=self.c.get('/game-tree').json;self.assertEqual(root['village_win'],str(expected));self.assertIsNone(root['actions'])
        snapshot=root['snapshot'];queue=[root['node']];seen=set();terminals=set()
        while queue:
            node=queue.pop()
            if node in seen:continue
            seen.add(node);r=self.c.get('/game-tree',query_string={'node':node,'snapshot':snapshot,'expand':'1'})
            self.assertEqual(r.status_code,200);d=r.json;self.assertEqual(d['evaluation'],'computed')
            if d['winner']:
                terminals.add(d['winner']);self.assertEqual(d['village_win'],'1' if d['winner']=='village' else '0');continue
            self.assertEqual(sum(F(a['policy_probability']) for a in d['actions']),1)
            for a in d['actions']:
                self.assertEqual(sum(F(b['probability']) for b in a['branches']),1)
                value=F()
                for b in a['branches']:
                    child=self.c.get('/game-tree',query_string={'node':b['node'],'snapshot':snapshot}).json
                    self.assertEqual(len(child['alive']),len(d['alive'])-1)
                    self.assertEqual(child['history'][-1]['target'],a['target'])
                    value+=F(b['probability'])*F(child['village_win']);queue.append(b['node'])
                self.assertEqual(value,F(a['village_win']))
        self.assertEqual(terminals,{'village','wolf'});self.assertGreater(len(seen),20)
    def test_existing_result_is_reused_and_inspection_does_not_edit_game(self):
        with self.c.session_transaction() as s:before=s['game'].copy()
        with patch('werewolf.calculation_tree.exchangeable_forecast', wraps=__import__('werewolf.exchangeable_public',fromlist=['exchangeable_forecast']).exchangeable_forecast) as evaluate:
            self.c.get('/main');self.assertEqual(evaluate.call_count,0)
            self.c.get('/game-tree?expand=1');count=evaluate.call_count;self.assertGreater(count,0)
            reused=self.c.get('/game-tree?expand=1').json;self.assertTrue(reused['reused']);self.assertEqual(evaluate.call_count,count)
        with self.c.session_transaction() as s:self.assertEqual(s['game'],before)
    def test_snapshot_change_unknown_node_and_default_off(self):
        root=self.c.get('/game-tree').json
        self.assertEqual(self.c.get('/game-tree?node=bad').status_code,404)
        with self.c.session_transaction() as s:g=s['game'];g['policy']['day']='random';g['revision']+=1;s['game']=g
        self.assertEqual(self.c.get('/game-tree',query_string={'snapshot':root['snapshot']}).status_code,409)
        plain=create_app({'TESTING':True,'SECRET_KEY':'default'}).test_client();self.assertEqual(plain.get('/game-tree').status_code,404)
    def test_scope_and_budget_are_explicit_without_approximate_results(self):
        self.c.post('/start',data={'players':'6','day':'max','night':'max'})
        self.assertEqual(self.c.get('/game-tree').status_code,422)
        self.c.post('/start',data={'players':'5','day':'max','night':'max'})
        self.app.config['MANUAL_CALC_MAX_WORK']=1
        r=self.c.get('/game-tree?expand=1');self.assertEqual(r.status_code,503);self.assertTrue(r.json['pending'])
    def test_nonexchangeable_evidence_does_not_use_count_inspector(self):
        from werewolf.calculation_tree import supported
        from werewolf.board_flow import BoardData
        from werewolf.exact import initial_board,replace_worlds
        with self.c.session_transaction() as session:data=BoardData.from_game(session['game'])
        board=replace_worlds(initial_board(5),((1,0,0,0,F(1,2)),(2,0,0,0,F(1,2))))
        self.assertFalse(supported(data,board))

    def test_random_policy_and_named_chance_weights_stay_exact(self):
        with self.c.session_transaction() as s:g=s['game'];g['policy']['day']='random';s['game']=g
        d=self.c.get('/game-tree?expand=1').json;self.assertEqual(d['mode'],'random')
        self.assertEqual({a['policy_probability'] for a in d['actions']},{'1/5'})
        self.assertEqual({b['probability'] for b in d['actions'][0]['branches']},{'1/5','4/5'})

if __name__=='__main__':unittest.main()
