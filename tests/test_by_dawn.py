from fractions import Fraction as F
import re
import unittest
from app import create_app
from werewolf.exact import initial_board, Rules, Strategy, action_outcomes
from werewolf.by_dawn import action_by_dawn

class ByDawnTests(unittest.TestCase):
    def test_five_players_excludes_tomorrows_execution(self):
        value=action_by_dawn(initial_board(5),1,Rules(),Strategy())
        self.assertEqual((value.village_win,value.wolf_win),(F(1,5),F(0)))
    def test_four_players_includes_night_defeat(self):
        value=action_by_dawn(initial_board(4),1,Rules(),Strategy())
        self.assertEqual((value.village_win,value.wolf_win),(F(1,4),F(3,4)))
    def test_six_players_two_wolves(self):
        value=action_by_dawn(initial_board(6,wolf_count=2),1,Rules(),Strategy())
        self.assertEqual((value.village_win,value.wolf_win),(F(0),F(2,3)))
    def test_legacy_night_stops_at_morning(self):
        b=next(o.board for o in action_outcomes(initial_board(5),1,Rules(),Strategy()) if not o.board.winner)
        value=action_by_dawn(b,2,Rules(),Strategy())
        self.assertEqual((value.village_win,value.wolf_win),(F(0),F(0)))
    def test_render_keeps_two_columns_and_exact_values(self):
        c=create_app({'TESTING':True,'SECRET_KEY':'horizon','HYBRID_TABLE_PREVIEW':True}).test_client()
        c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
        h=c.get('/main').get_data(as_text=True)
        self.assertIn('今日中勝率',h);self.assertIn('期待勝率',h)
        dawn=re.search(r'data-win-horizon="dawn">(.*?)</td>',h,re.S).group(1)
        final=re.search(r'data-win-horizon="final">(.*?)</td>',h,re.S).group(1)
        self.assertIn('data-fraction="1/5"',dawn);self.assertIn('data-fraction="0"',dawn)
        self.assertIn('data-fraction="7/15"',final);self.assertIn('data-fraction="8/15"',final)
    def test_night_policy_uses_final_win_scores_and_averages_exact_ties(self):
        from werewolf.exact import replace_worlds
        b=replace_worlds(initial_board(4),((1,0,0,0,F(1)),))
        rules=Rules(allow_self_bite=True)
        strategy=Strategy(include_self_bite=True)
        # Execute a known citizen. Deliberate score callback verifies that the
        # horizon itself is not used as the optimisation objective.
        pick_wolf=lambda child:((t,F(0) if t==1 else F(1)) for t in child.alive)
        value=action_by_dawn(b,4,rules,strategy,pick_wolf)
        self.assertEqual((value.village_win,value.wolf_win),(F(1),F(0)))
        ties=lambda child:((t,F(1,2)) for t in child.alive)
        value=action_by_dawn(b,4,rules,strategy,ties)
        self.assertEqual((value.village_win,value.wolf_win),(F(1,3),F(2,3)))
        value=action_by_dawn(b,4,rules,Strategy(night='random',include_self_bite=True))
        self.assertEqual((value.village_win,value.wolf_win),(F(1,3),F(2,3)))
    def test_horizon_is_part_of_final_win_not_an_extra_probability(self):
        from werewolf.exact import legal_targets,value_for_action
        for n in range(3,8):
            for wolves in range(1,(n-1)//2+1):
                for mode in ('random','max'):
                    for self_bite in (False,True):
                        rules=Rules(allow_self_bite=self_bite)
                        strategy=Strategy(night=mode,include_self_bite=self_bite)
                        b=initial_board(n,wolf_count=wolves)
                        for t in legal_targets(b,rules,strategy):
                            horizon=action_by_dawn(b,t,rules,strategy)
                            final=value_for_action(b,t,rules,strategy)
                            self.assertLessEqual(horizon.village_win,final.village_win)
                            self.assertLessEqual(horizon.wolf_win,final.wolf_win)
    def test_seer_forecast_reports_horizon_with_private_history_preserved(self):
        from dataclasses import replace
        from werewolf.exact import replace_worlds
        from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.seer_future_forecast import forecast
        worlds=((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
        b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
        s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
        past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
        result=forecast(b,s,past,Rules(),Strategy())
        self.assertEqual(len(result.by_dawn_values),5)
        for t,horizon in result.by_dawn_values:
            final=dict(result.action_values)[t]
            self.assertLessEqual(horizon.village_win,final)
            self.assertLessEqual(horizon.wolf_win,1-final)
