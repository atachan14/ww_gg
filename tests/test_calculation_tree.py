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
        self.c=self.app.test_client();self.c.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
    def test_real_root_group_masses_named_Boards_and_terminal_values(self):
        expected=independent((1,2,3,4,5),tuple((p,F(1,5)) for p in range(1,6)),'day')
        root=self.c.get('/game-tree?expand=1').json
        self.assertEqual(root['village_win'],str(expected));self.assertEqual(root['players'][0]['seer_probability'],'1/5')
        self.assertEqual(len(root['actions']),1);a=root['actions'][0]
        self.assertEqual(a['targets'],[1,2,3,4,5]);self.assertEqual(a['multiplicity'],5)
        self.assertEqual(a['policy_probability'],'1')
        self.assertEqual({b['probability'] for b in a['branches']},{'1/5','4/5'})
        for branch in a['branches']:
            self.assertEqual(len(branch['variants']),5)
            self.assertEqual(sum(F(v['mixture_probability']) for v in branch['variants']),F(branch['probability']))
            for v in branch['variants']:
                d=self.c.get('/game-tree',query_string={'node':v['node']}).json
                self.assertEqual(d['history'][-1]['target'],v['target'])
                self.assertEqual(d['village_win'],'1' if d['winner']=='village' else '1/3')
        queue=[root];seen=set();terminal=set()
        while queue:
            d=queue.pop()
            if d['node'] in seen:continue
            seen.add(d['node'])
            if d['winner']:terminal.add(d['winner']);continue
            d=self.c.get('/game-tree',query_string={'node':d['node'],'expand':'1'}).json
            self.assertIn('actions',d,d)
            self.assertEqual(sum(F(a['policy_probability']) for a in d['actions']),1)
            for a in d['actions']:
                self.assertEqual(sum(F(b['probability']) for b in a['branches']),1)
                for branch in a['branches']:queue.append(d['items'][branch['node']])
        self.assertEqual(terminal,{'village','wolf'})
    def test_full_keys_preserve_named_state_and_cold_forecasts(self):
        from werewolf.board_flow import BoardData
        from werewolf.calculation_tree import CalculationTree
        with self.c.session_transaction() as session:data=BoardData.from_game(session['game'])
        roles=data.roles();tree=CalculationTree(data,roles.board,roles.forecast());tree.expand(tree.root)
        for action in tree.nodes[tree.root]['actions']:
            for branch in action['branches']:
                keys=set()
                for variant in branch['variants']:
                    row=tree.nodes[variant['node']];node=row['node'];keys.add(tree.equivalence(node))
                    from werewolf.information_set_forecast import InformationSetForecast
                    cold=node.export_request().roles();engine=InformationSetForecast(tree.rules,tree.strategy,exact_renaming=False,retire_uninformative_scans=False)
                    engine.retain_joint_guard_history=True
                    with tree.calculation._ClosedCalculation__kernel():expected=engine.solve(*cold,physical=cold.physical)
                    self.assertEqual(tree.value(variant['node']),expected)
                self.assertEqual(len(keys),1)
        # Equal scalar values do not make different physical histories identical.
        win=tree.nodes['1']['node'];night=tree.nodes['2']['node'];tree.expand('2')
        day=tree.nodes[tree.nodes['2']['actions'][0]['branches'][0]['node']]['node']
        day_id=tree.register(day);tree.expand(day_id)
        later=[tree.nodes[b['node']]['node'] for a in tree.nodes[day_id]['actions'] for b in a['branches'] if tree.nodes[b['node']]['node'].read().public.winner=='village'][0]
        self.assertEqual(tree.value(tree.register(win)),tree.value(tree.register(later)))
        self.assertNotEqual(tree.equivalence(win),tree.equivalence(later))
    def test_inspection_is_cached_and_does_not_edit_saved_inputs(self):
        with self.c.session_transaction() as s:before=s['game'].copy()
        first=self.c.get('/game-tree?expand=1').json
        self.assertEqual(first,self.c.get('/game-tree?expand=1').json)
        with self.c.session_transaction() as s:self.assertEqual(before,s['game'])
    def test_snapshot_change_unknown_node_and_default_off(self):
        root=self.c.get('/game-tree').json
        self.assertEqual(self.c.get('/game-tree?node=bad').status_code,404)
        with self.c.session_transaction() as s:g=s['game'];g['revision']+=1;s['game']=g
        self.assertEqual(self.c.get('/game-tree',query_string={'snapshot':root['snapshot']}).status_code,409)
        plain=create_app({'TESTING':True,'SECRET_KEY':'default'}).test_client();self.assertEqual(plain.get('/game-tree').status_code,404)
    def test_scope_and_budget_are_explicit_without_approximate_results(self):
        self.c.post('/start',data={'players':'6','day':'max','night':'max'})
        self.assertEqual(self.c.get('/game-tree').status_code,422)
        self.c.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
        self.app.config['MANUAL_CALC_MAX_WORK']=1
        r=self.c.get('/game-tree?expand=1');self.assertEqual(r.status_code,503);self.assertTrue(r.json['pending'])
    def test_ordinary_top_form_defaults_report_actual_mismatch_without_edit(self):
        from html.parser import HTMLParser
        class Form(HTMLParser):
            def __init__(self):super().__init__();self.fields={};self.select=None
            def handle_starttag(self,tag,attrs):
                d=dict(attrs)
                if tag=='input' and 'name' in d:self.fields[d['name']]=d.get('value','')
                if tag=='select':self.select=d.get('name')
                if tag=='option' and self.select and ('selected' in d or self.select not in self.fields):self.fields[self.select]=d.get('value','')
            def handle_endtag(self,tag):
                if tag=='select':self.select=None
        client=self.app.test_client();form=Form();form.feed(client.get('/').data.decode());payload=form.fields
        self.assertEqual((payload['citizens'],payload['seers']),('4','0'))
        client.post('/start',data=payload)
        with client.session_transaction() as session:before=session['game'].copy()
        response=client.get('/game-tree?expand=1');self.assertEqual(response.status_code,422)
        self.assertEqual(response.json['reason'],'game_tree_scope')
        self.assertEqual(response.json['actual']['counts']['citizens'],4)
        self.assertEqual(response.json['actual']['counts']['seers'],0)
        self.assertTrue(response.json['issues']);self.assertEqual(response.json['settings_url'],'/')
        with client.session_transaction() as session:self.assertEqual(session['game'],before)
        page=client.get('/main').data.decode();self.assertIn('市民4・占い0',page)
        payload.update(citizens='3',seers='1');client.post('/start',data=payload)
        self.assertEqual(client.get('/game-tree?expand=1').json['village_win'],'7/15')
    def test_precise_rule_and_policy_rejections_keep_saved_conditions(self):
        for change,expected in [({'allow_self_bite':'1'},'自噛み'),({'initial_seer':'normal'},'ランダム白'),({'day':'random'},'混在')]:
            client=self.app.test_client();client.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max',**change})
            with client.session_transaction() as session:before=session['game'].copy()
            result=client.get('/game-tree?expand=1');self.assertEqual(result.status_code,422)
            self.assertTrue(any(expected in text for text in result.json['issues']),result.json)
            with client.session_transaction() as session:self.assertEqual(before,session['game'])
    def test_existing_all_random_entry_still_uses_actual_policy(self):
        client=self.app.test_client();client.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'random','night':'random','fake_reports':'random'})
        response=client.get('/game-tree?expand=1');self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['mode'],'random');self.assertEqual(response.json['policy']['fake_reports'],'random')
    def test_unsupported_policy_is_explicit(self):
        with self.c.session_transaction() as s:g=s['game'];g['policy']['day']='random';s['game']=g
        self.assertEqual(self.c.get('/game-tree?expand=1').status_code,422)

if __name__=='__main__':unittest.main()
