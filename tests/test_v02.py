import unittest
from fractions import Fraction as F
from werewolf.exact import (Board, Progress, Rules, Strategy, Values, action_outcomes,
 advance, build_tree, evaluate_tree, initial_board, solve, symmetric_action)
from app import create_app


def exhaustive(node, strategy):
    if node.board.winner:
        return F(node.board.winner == 'village')
    candidates = [sum((c.probability * exhaustive(c.child, strategy) for c in a.outcomes), F(0))
                  for a in node.actions]
    mode = strategy.day if node.board.phase == 'day' else strategy.night
    return sum(candidates, F(0)) / len(candidates) if mode == 'random' else (max(candidates) if node.board.phase == 'day' else min(candidates))


class MultipleWolfTests(unittest.TestCase):
    def test_seven_two_wolves_next_morning_and_correlations(self):
        p = advance(Progress(initial_board(7, 2)), 1, Rules(), Strategy())
        self.assertEqual(p.board.wolf_count_distribution, {1:F(2,7),2:F(5,7)})
        self.assertEqual(p.board.wolf_probability(1), F(2,7))
        self.assertIsNone(p.board.wolf_count)
        p = advance(p, 2, Rules(), Strategy())
        self.assertEqual((p.board.day, p.board.phase), (2,'day'))
        self.assertEqual(p.board.wolf_count_distribution, {1:F(2,7),2:F(5,7)})
        self.assertEqual(p.board.wolf_probability(2), 0)
        self.assertEqual(p.board.wolf_probability(1), F(2,7))
        self.assertEqual(p.board.wolf_probability(3), F(12,35))
        self.assertEqual(p.board.joint_wolf_probability((3,4)), F(1,14))
        self.assertNotEqual(p.board.joint_wolf_probability((3,4)), p.board.wolf_probability(3)*p.board.wolf_probability(4))
        self.assertEqual(p.active_mass, 1)

    def test_small_multiwolf_exact_reference_values(self):
        for n,w,no_bite,bite in [(5,2,F(2,15),F(1,5)),(6,2,F(1,12),F(1,3)),(7,2,F(8,35),F(3,7)),(7,3,F(2,35),F(1,7))]:
            for included, expected in [(False,no_bite),(True,bite)]:
                policy=Strategy(include_self_bite=included)
                root=build_tree(initial_board(n,w),Rules(True),policy)
                self.assertEqual(evaluate_tree(root,policy).board_value(root).village_win,expected)

    def test_explicit_unshared_complete_tree_agrees_with_cached_evaluation(self):
        for n,w in [(3,1),(4,1),(5,1),(5,2),(6,2)]:
            for included in (False,True):
                for mode in ('max','random'):
                    strategy=Strategy(mode,mode,included)
                    root=build_tree(initial_board(n,w),Rules(True),strategy)
                    self.assertEqual(evaluate_tree(root,strategy).board_value(root).village_win, exhaustive(root,strategy))

    def test_initial_joint_counts_and_symmetry(self):
        for n in range(3,10):
            for w in range(1,(n-1)//2+1):
                b=initial_board(n,w)
                self.assertEqual(sum(b.wolf_probability(i) for i in b.alive),w)
                self.assertEqual(b.joint_wolf_probability((1,2)), F(w*(w-1), n*(n-1)))
                for include in (False,True):
                    s=Strategy(include_self_bite=include)
                    root=build_tree(b,Rules(True),s); e=evaluate_tree(root,s)
                    self.assertEqual({e.action_value(root,i) for i in b.alive},{e.board_value(root)})

    def test_all_counts_full_manual_histories_mass_and_terminal_rules(self):
        for n in range(3,10):
            for w in range(1,(n-1)//2+1):
                for included in (False,True):
                    policy=Strategy(include_self_bite=included); rules=Rules(True)
                    p=Progress(initial_board(n,w))
                    expected=evaluate_tree(build_tree(p.board,rules,policy),policy).board_value(build_tree(p.board,rules,policy))
                    for target in range(1,n):
                        if p.finished: break
                        outcomes=action_outcomes(p.board,target,rules,policy)
                        self.assertEqual(sum(o.probability for o in outcomes),1)
                        for o in outcomes:
                            if o.board.winner == 'village': self.assertEqual(set(o.board.wolf_count_distribution),{0})
                            if o.board.winner == 'wolf': self.assertTrue(all(2*w >= len(o.board.alive) for w in o.board.wolf_count_distribution))
                        p=advance(p,target,rules,policy)
                        self.assertEqual(p.active_mass+p.settled_village+p.settled_wolf,1)
                    self.assertTrue(p.finished)
                    self.assertEqual(p.total_values(),expected)

    def test_public_optimization_precedes_hidden_assignment(self):
        b=Board(3,(1,2,3),1,belief=((1,F(3,5)),(2,F(3,10)),(4,F(1,10))))
        root=build_tree(b,Rules(),Strategy())
        self.assertEqual(evaluate_tree(root,Strategy()).board_value(root).village_win,F(3,5))
        self.assertEqual(evaluate_tree(root,Strategy('random')).board_value(root).village_win,F(1,3))

    def test_validation_and_terminal(self):
        for n,w in [(3,2),(5,3),(9,5),(7,0),(7,True),(True,1),(10,1)]:
            with self.assertRaises(ValueError): initial_board(n,w)
        for belief in [((1,F(1,2)),),((1,F(1,2)),(1,F(1,2))),((1,1),)]:
            with self.assertRaises(ValueError): Board(3,(1,2,3),None,belief=belief)


class MultiWolfWebTests(unittest.TestCase):
    def test_seven_two_wolves_ui_back_history_and_strategy(self):
        app=create_app({'TESTING':True,'SECRET_KEY':'test'}); c=app.test_client()
        self.assertEqual(c.post('/start',data={'players':'7','wolves':'2','day':'max','night':'max'}).status_code,303)
        def state():
            with c.session_transaction() as session: return session['game']
        def form(target=None,**changes):
            d={'revision':str(state()['revision']),'day':'max','night':'max'}
            if target: d['target']=str(target)
            return {**d,**changes}
        for i in (1,2): self.assertEqual(c.post('/advance',data=form(i)).status_code,303)
        html=c.get('/main').get_data(as_text=True)
        self.assertIn('1w',html); self.assertIn('2w',html)
        self.assertIn('data-fraction="2/7"',html); self.assertIn('data-fraction="5/7"',html)
        before=state()['history']
        self.assertEqual(c.post('/strategy',data=form(3,day='random',night='random')).status_code,303)
        self.assertEqual(state()['history'],before)
        self.assertEqual(c.post('/back',data={'revision':str(state()['revision'])}).status_code,303)
        self.assertEqual(state()['selection'],2)
        self.assertEqual(state()['policy']['day'],'max')
        self.assertEqual(len(state()['history']),1)

    def test_nine_complete_web_history_and_tampered_cast(self):
        app=create_app({'TESTING':True,'SECRET_KEY':'test'}); c=app.test_client()
        for n,w in [('3','2'),('9','5'),('7','0')]:
            self.assertEqual(c.post('/start',data={'players':n,'wolves':w,'day':'max','night':'max'}).status_code,400)
        self.assertEqual(c.post('/start',data={'players':'9','wolves':'3','day':'max','night':'max'}).status_code,303)
        for i in range(1,8):
            with c.session_transaction() as session: revision=session['game']['revision']
            res=c.post('/advance',data={'revision':str(revision),'target':str(i),'day':'max','night':'max'})
            self.assertEqual(res.status_code,303)
            html=c.get(res.location).get_data(as_text=True)
            if 'data-screen="result"' in html: break
        self.assertIn('data-screen="result"',html)

