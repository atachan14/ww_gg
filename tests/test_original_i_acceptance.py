"""Finite original ①: unknown uniform hunter / configured wolf max."""
import unittest
from copy import deepcopy
from fractions import Fraction as F
from unittest.mock import patch
import tests.test_root_guard_max as fixture
import werewolf.root_secret_flow as root
from werewolf.seer_manual import migrate_game,replay
from werewolf.model_a_public import evaluate_public_game,clear_public_cache
from werewolf.private_adapter import evaluate_private_table
from werewolf.exact import Strategy
from werewolf.seer_future_uniform import FuturePending

class OriginalIAcceptanceTests(unittest.TestCase):
    def test_two_gj_saved_policies_owned_records_and_unfiltered_replay(self):
        expected={(True,'max'):F(13,48),(True,'random'):F(53,204),
                  (False,'max'):F(10,39),(False,'random'):F(28,111)}
        for repeat in (True,False):
            for saved in ('max','random'):
                with self.subTest(repeat=repeat,saved=saved):
                    g=fixture.RootGuardMaxTests().game(repeat,players=6)
                    gj=dict(target=None,claims=g['claims'],claim_policy=g['claim_policy'],
                            policy=g['policy'],observation='night-deaths-v1',deaths=[])
                    day=dict(target=3,claims=g['claims'],claim_policy=g['claim_policy'],policy=g['policy'])
                    g=migrate_game({**g,'history':[g['history'][0],
                        {**gj,'policy':{**g['policy'],'night':saved}},day,gj]})
                    before=deepcopy(g);rules,p=replay(g);strategy=Strategy(**g['policy'])
                    branch=root.prepare_root_entry(g,p.board,rules,strategy)
                    self.assertNotIsInstance(branch,FuturePending)
                    original=root.step_root_action
                    def unfiltered(*args,**kwargs):
                        kwargs['_observed_alive']=None
                        return original(*args,**kwargs)
                    with patch.object(root,'step_root_action',side_effect=unfiltered):
                        reference=root.replay_root_secrets(g,p.board,rules,strategy)
                    self.assertEqual(branch,reference)
                    self.assertTrue(all(len(h.guards)==len(h.attacks)==2
                                        for h in branch.physical_law.hypotheses))
                    clear_public_cache()
                    public=evaluate_public_game(g,p.board,rules,strategy)
                    self.assertNotIsInstance(public,FuturePending)
                    self.assertEqual(public.village_win,expected[repeat,saved])
                    owned=sorted({tuple((a.night,a.target) for a in h.attacks)
                        for h in branch.physical_law.hypotheses if h.roles[0]==1})
                    record=next(a for a in owned if a[0][1]==2)
                    self.assertEqual(record,((1,2),(2,2 if repeat else 4)))
                    evidence=[dict(day=d,target=t,color=None) for d,t in record]
                    table=evaluate_private_table(p.board,'wolf',[1],evidence,rules,strategy,game_state=g)
                    rows={x['id']:x['final'] for x in table['players'] if x['legal']}
                    self.assertTrue(all(x is not None for x in rows.values()))
                    self.assertEqual(rows[1]['village'],'1')
                    self.assertEqual(rows[2]['village'],'1/12' if repeat else '0')
                    self.assertEqual(rows[4]['village'],'0');self.assertEqual(rows[5]['village'],'0')
                    self.assertEqual(evaluate_public_game(g,p.board,rules,strategy),public)
                    self.assertEqual(g,before)
