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
            # The group is one decision; variants are the concrete name
            # recipes. Uniform named choice contributes 1/5 of each event.
            self.assertEqual(sorted(v['target'] for v in branch['variants']),list(range(1,6)))
            self.assertEqual(sum(F(v['mixture_probability']) for v in branch['variants']),F(branch['probability']))
            for variant in branch['variants']:
                hit=F(1,5);event=hit if branch['probability']=='1/5' else 1-hit
                self.assertEqual(F(variant['conditional_probability']),event)
                self.assertEqual(F(variant['mixture_probability']),event/F(5))
            for v in branch['variants']:
                d=self.c.get('/game-tree',query_string={'node':v['node']}).json
                self.assertEqual(d['history'][-1]['target'],v['target'])
                for player in d['players']:
                    expected_wolf=F(int(player['player']==v['target'])) if d['winner']=='village' else F(int(player['player']!=v['target']),4)
                    self.assertEqual(F(player['wolf_probability']),expected_wolf)
                    self.assertEqual(F(player['physical_wolf_probability']),expected_wolf)
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
        response=self.c.get('/game-tree');self.assertEqual(response.status_code,200)
        expected=independent(tuple(range(1,7)),tuple((p,F(1,6)) for p in range(1,7)),'day')
        self.assertEqual(expected,F(3,8));self.assertEqual(F(response.json['village_win']),expected)
        self.assertEqual(response.json['alive'],list(range(1,7)))
        self.assertNotIn('unsupported',response.json)
        self.c.post('/start',data={'players':'5','seers':'1','day':'max','night':'max'})
        self.app.config['MANUAL_CALC_MAX_WORK']=1
        r=self.c.get('/game-tree?expand=1');self.assertEqual(r.status_code,503);self.assertTrue(r.json['pending'])
        self.assertEqual(r.json['budget_kind'],'work');self.assertNotIn('village_win',r.json)
        self.app.config['MANUAL_CALC_MAX_WORK']=4000000
        recovered=self.c.get('/game-tree?expand=1');self.assertEqual(recovered.status_code,200)
        self.assertEqual(F(recovered.json['village_win']),independent((1,2,3,4,5),tuple((p,F(1,5)) for p in range(1,6)),'day'))
    def test_ordinary_top_form_submits_only_its_controls_without_edit(self):
        from html.parser import HTMLParser
        from copy import deepcopy
        class Form(HTMLParser):
            """Successful controls associated with setup-form, not all forms."""
            def __init__(self):super().__init__();self.fields={};self.form=None;self.select=None
            def handle_starttag(self,tag,attrs):
                d=dict(attrs)
                if tag=='form':self.form=d.get('id')
                owner=d.get('form',self.form)
                if tag=='input' and owner=='setup-form' and 'name' in d and 'disabled' not in d:
                    if d.get('type') not in ('checkbox','radio') or 'checked' in d:self.fields[d['name']]=d.get('value','')
                if tag=='select':self.select=(d['name'],[]) if owner=='setup-form' and 'name' in d and 'disabled' not in d else None
                if tag=='option' and self.select:self.select[1].append((d.get('value',''),'selected' in d))
            def handle_endtag(self,tag):
                if tag=='form':self.form=None
                if tag=='select' and self.select:
                    name,options=self.select
                    self.fields[name]=next((v for v,selected in options if selected),options[0][0])
                    self.select=None
        client=self.app.test_client();form=Form();form.feed(client.get('/').get_data(as_text=True));payload=form.fields
        self.assertEqual((payload['citizens'],payload['seers']),('4','0'))
        self.assertNotIn('probability-format',payload)
        started=client.post('/start',data=payload);self.assertEqual(started.status_code,303)
        with client.session_transaction() as session:before=deepcopy(session['game'])
        response=client.get('/game-tree?expand=1');self.assertEqual(response.status_code,200)
        self.assertEqual(F(response.json['village_win']),independent((1,2,3,4,5),tuple((p,F(1,5)) for p in range(1,6)),'day'))
        self.assertTrue(all(p['seer_probability']=='0' for p in response.json['players']))
        with client.session_transaction() as session:self.assertEqual(session['game'],before)
        # Unrelated display controls must not be accepted as game-rule input.
        self.assertEqual(client.post('/start',data={**payload,'probability-format':'fraction'}).status_code,400)
        with client.session_transaction() as session:self.assertEqual(session['game'],before)
        payload.update(citizens='3',seers='1');self.assertEqual(client.post('/start',data=payload).status_code,303)
        result=client.get('/game-tree?expand=1');self.assertEqual(result.status_code,200)
        self.assertEqual(F(result.json['village_win']),F(7,15))
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
    def test_terminal_columns_use_arrival_slot_without_changing_solver_phase(self):
        root=self.c.get('/game-tree?expand=1').json
        win=root['items']['1'];self.assertEqual((win['column_day'],win['column_phase']),(1,'night'))
        self.assertEqual((win['day'],win['phase'],win['village_win']),(1,'day','1'))
        night=self.c.get('/game-tree?node=2&expand=1').json
        day_id=night['actions'][0]['branches'][0]['node']
        day=self.c.get('/game-tree',query_string={'node':day_id,'expand':'1'}).json
        terminals=[d for d in day['items'].values() if d['winner']]
        self.assertEqual({d['winner'] for d in terminals},{'village','wolf'})
        for d in terminals:
            self.assertEqual((d['column_day'],d['column_phase']),(2,'night'))
            self.assertEqual((d['day'],d['phase']),(2,'day'))
    def test_existing_advance_cannot_select_terminal_physical_outcome(self):
        root=self.c.get('/game-tree?expand=1').json
        terminal=root['items']['1'];self.assertEqual(terminal['village_win'],'1')
        with self.c.session_transaction() as s:revision=s['game']['revision']
        response=self.c.post('/advance',data={'revision':revision,'target':'1','day':'max','night':'max'})
        self.assertEqual(response.status_code,303)
        from werewolf.board_flow import BoardData
        with self.c.session_transaction() as s:roles=BoardData.from_game(s['game']).roles()
        self.assertFalse(roles.progress.finished)
        self.assertEqual(roles.board.phase,'night')
        self.assertEqual(roles.forecast().village_win,F(1,3))
        self.assertNotEqual(roles.board.winner,terminal['winner'])
    def test_unsupported_policy_is_explicit(self):
        with self.c.session_transaction() as s:g=s['game'];g['policy']['day']='random';s['game']=g
        self.assertEqual(self.c.get('/game-tree?expand=1').status_code,422)

if __name__=='__main__':unittest.main()
