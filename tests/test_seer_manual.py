import unittest,json,copy
from fractions import Fraction as F
from itertools import combinations
from unittest.mock import patch
from app import create_app
from werewolf.seer_manual import replay,pending,MODE
from werewolf.exact import value_for_action,Strategy,Rules

def literal_first_values(g):
    # Independent 30-role enumeration + PUBLIC forced-legal-bite contract.
    # No normal solver/transition, no role-specific future acquisition.
    worlds=[]
    for wolves in combinations(range(1,6),2):
        for seer in range(1,6):
            if seer in wolves:continue
            if seer not in (1,2) or (2 if seer==1 else 1) not in wolves:continue
            q=F(1,6)
            for row in g['seer_inputs']:
                if row['day']!=1 or row['target'] is None or row['color'] is None:continue
                if row['reporter']==seer:
                    if (row['target'] in wolves)!=(row['color']=='black'):q=F();break
                    if g['seer_options']['initial_rule']=='random_white':
                        if row['color']!='white':q=F();break
                        q/=2
            if q:worlds.append((frozenset(wolves),seer,q))
    total=sum(q for w,s,q in worlds);worlds=[(w,s,q/total) for w,s,q in worlds]
    result={}
    for executed in range(1,6):
        live=[(w-{executed},s,q) for w,s,q in worlds if executed in w]
        reach=sum(q for w,s,q in live)
        if not reach:result[executed]=F();continue
        live=[(w,s,q/reach) for w,s,q in live];alive=set(range(1,6))-{executed};values=[]
        for bitten in sorted(alive):
            valid=[(w,s,q) for w,s,q in live if bitten not in w];mass=sum(q for w,s,q in valid)
            if not mass:continue
            votes=[sum(q for w,s,q in valid if target in w)/mass for target in alive-{bitten}]
            values.append(max(votes) if g['policy']['day']=='max' else sum(votes,F())/len(votes))
        continuation=min(values) if g['policy']['night']=='max' else sum(values,F())/len(values)
        result[executed]=reach*continuation
    return result

class SeerManualTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'manual-test'});self.client=self.app.test_client()
        self.assertEqual(self.client.post('/start',data={'citizens':'2','mediums':'0','seers':'1','hunters':'0','wolves':'2','seer_mode':MODE,'day':'max','night':'max','allow_self_bite':'0','include_self_bite':'0'}).status_code,303)
    def game(self):
        with self.client.session_transaction() as s:return copy.deepcopy(s['game'])
    def form(self,**extra):
        g=self.game();f={'revision':str(g['revision']),'day':g['policy']['day'],'night':g['policy']['night'],'include_self_bite':'0'}
        f.update({f'co_{i}':c for i,c in enumerate(g['claims'],1)});f.update(extra);return f
    def configured(self,initial='normal',reports=True):
        self.assertEqual(self.client.post('/start',data={'citizens':'2','seers':'1','wolves':'2','initial_seer':initial,'day':'max','night':'max'}).status_code,303)
        fields={'co_1':'seer','co_2':'seer'}
        if reports:fields.update(seer_target_1_1='3',seer_color_1_1='white',seer_target_1_2='3',seer_color_1_2='black')
        self.assertEqual(self.client.post('/strategy',data=self.form(**fields)).status_code,303)
    def advance(self,target):self.assertEqual(self.client.post('/advance',data=self.form(target=str(target))).status_code,303)

    def test_fixed_handling_and_game_rule_readonly_in_main(self):
        html=self.client.get('/main').data
        self.assertIn(b'id="view-first-seer" disabled',html)
        self.assertNotIn(b'name="seer_likelihood"',html)
        self.assertNotIn(b'name="seer_initial_rule"',html)
        self.assertIsNone(pending(self.game()))

    def test_fixed_defaults_calculate_without_unselected_gate(self):
        g=self.game();self.assertEqual(g['seer_options'],{'initial_rule':'random_white','likelihood':'compatibility'})
        html=self.client.get('/main').data;self.assertNotIn(b'data-seer-pending',html);self.assertIn(b'id="village-rate"',html)

    def test_independent_enumeration_all_targets_colors_and_future_modes(self):
        self.configured(reports=False);base=self.game()
        for initial in ('normal','random_white'):
            for a,b in (('white','white'),('white','black'),('black','white')):
                for day,night in (('max','max'),('random','random')):
                    g=copy.deepcopy(base);g['seer_options']['initial_rule']=initial;g['rules']['initial_seer']=initial;g['policy'].update(day=day,night=night)
                    g['seer_inputs']=[{'day':1,'reporter':1,'target':3,'color':a},{'day':1,'reporter':2,'target':3,'color':b}]
                    rules,p=replay(g);expected=literal_first_values(g)
                    self.assertEqual({t:value_for_action(p.board,t,rules,Strategy(**g['policy'])).village_win for t in p.board.alive},expected)

    def test_conditioning_cache_change_and_probabilities_not_win_rate(self):
        self.configured();g=self.game();rules,p=replay(g)
        self.assertEqual(len(p.board.worlds),3);self.assertEqual(p.board.wolf_probability(2),F(2,3))
        self.assertTrue(all(value_for_action(p.board,t,rules,Strategy(**g['policy'])).village_win==F(1,3) for t in p.board.alive))
        changed=copy.deepcopy(g);changed['seer_inputs'][1]['color']='white'
        self.assertEqual(replay(changed)[1].board.wolf_probability(2),F(1,2));self.assertEqual(replay(g), (rules,p))

    def test_partial_fields_are_saved_as_draft_and_pending(self):
        self.configured(reports=False)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_1_1='3',seer_color_1_1='')).status_code,303)
        self.assertIsNotNone(pending(self.game()));self.assertEqual(self.game()['seer_inputs'][0]['target'],3)
        self.assertIn(b'data-seer-pending',self.client.get('/main').data)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_1_1='3',seer_color_1_1='white')).status_code,303)
        self.assertIsNone(pending(self.game()))

    def test_each_day_results_and_dead_target_at_scan_roster(self):
        self.configured();self.advance(2);self.advance(3)
        html=self.client.get('/main').data;self.assertIn(b'seer_target_2_1',html)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_1='3',seer_color_2_1='white')).status_code,303)
        self.assertEqual(len(self.game()['seer_inputs']),3)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_2='4',seer_color_2_2='white')).status_code,400)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_1='2',seer_color_2_1='white')).status_code,400)

    def test_dead_reporter_evidence_is_retained_and_replay_edits_from_origin(self):
        self.configured();self.advance(2);g=self.game();policies=copy.deepcopy(g['history'])
        self.assertEqual(len(g['seer_inputs']),2);self.assertIn(b'seer_target_1_2',self.client.get('/main').data)
        before=replay(g)[1].settled_wolf
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_1_2='3',seer_color_1_2='white')).status_code,303)
        after=self.game();self.assertEqual(after['history'],policies);self.assertNotEqual(replay(after)[1].settled_wolf,before)
        self.assertEqual(after['seer_inputs'][1]['reporter'],2)

    def test_initial_white_likelihood_and_none_allow_later_days(self):
        self.configured(initial='random_white');p=replay(self.game())[1];self.assertEqual(p.board.wolf_probability(2),F(1))
        # New isolated no-initial game, but Day2 still accepts input.
        self.setUp();self.configured(initial='none',reports=False);self.advance(2);self.advance(3)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_1='4',seer_color_2_1='black')).status_code,303)
        self.assertEqual(replay(self.game())[1].board.wolf_probability(4),F(1))

    def test_invalid_and_contradictory_inputs_atomic_and_stale_revision_rejected(self):
        self.configured();before=self.game()
        for args in [dict(seer_target_1_1='1',seer_color_1_1='white'),dict(seer_target_1_1='2',seer_color_1_1='white',seer_target_1_2='1',seer_color_1_2='white'),dict(seer_target_2_1='3',seer_color_2_1='white')]:
            self.assertEqual(self.client.post('/strategy',data=self.form(**args)).status_code,400);self.assertEqual(self.game(),before)
        self.assertEqual(self.client.post('/strategy',data=self.form(revision='999')).status_code,409);self.assertEqual(self.game(),before)

    def test_back_discards_future_reports_and_cookie_cold_restore(self):
        self.configured();self.advance(2);self.advance(3)
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_1='4',seer_color_2_1='black')).status_code,303)
        g=self.game();cookie=self.client.get_cookie('session').value
        other=self.app.test_client();other.set_cookie('session',cookie);self.assertEqual(other.get('/main').status_code,200)
        with other.session_transaction() as sess:self.assertEqual(sess['game'],g)
        self.assertEqual(self.client.post('/back',data={'revision':g['revision']}).status_code,303)
        self.assertTrue(all(r['day']==1 for r in self.game()['seer_inputs']));self.assertEqual(self.client.get('/main').status_code,200)

    def test_rules_and_co_locked_after_progress(self):
        self.configured();self.advance(2);before=self.game()
        self.assertEqual(self.client.post('/strategy',data=self.form(seer_initial_rule='random_white')).status_code,400)
        self.assertEqual(self.client.post('/strategy',data=self.form(co_1='latent')).status_code,400)
        self.assertEqual(self.game(),before)

    def test_no_future_seer_components_called_and_reaches_terminal(self):
        with patch.dict('sys.modules',{'werewolf.seer_perspectives':None,'werewolf.seer_acquisition':None,'werewolf.seer_api':None,'werewolf.hunter_runtime':None}):
            self.configured();self.advance(2);self.advance(3)
            self.assertEqual(self.client.post('/strategy',data=self.form(seer_target_2_1='4',seer_color_2_1='black')).status_code,303)
            self.advance(4);self.assertEqual(self.client.get('/result').status_code,200)
            self.assertEqual(len(self.game()['history']),3)

    def test_general_cast_allowed_invalid_cast_and_legacy_unchanged(self):
        data={'players':'4','wolves':'1','seers':'1','mediums':'0','hunters':'0','seer_mode':MODE,'day':'max','night':'max'}
        self.assertEqual(self.client.post('/start',data=data).status_code,303)
        self.assertEqual(self.client.post('/start',data={**data,'players':'10'}).status_code,400)
        data.pop('seer_mode');self.assertEqual(self.client.post('/start',data=data).status_code,303)
        self.assertEqual(self.game()['seer_mode'],MODE);self.assertEqual(self.client.get('/main').status_code,200)
