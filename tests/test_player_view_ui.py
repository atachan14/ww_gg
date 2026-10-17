import copy,json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from flask import template_rendered
from app import create_app
from werewolf.player_view import PlayerData
from werewolf.seer_future_uniform import FuturePending

class PlayerViewUIReadTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'player-ui','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'CALCULATION_POSITION_ENABLED':False})
        self.c=self.app.test_client();self.c.post('/start',data={'citizens':'4','wolves':'1','day':'random','night':'random'})
    def game(self):
        with self.c.session_transaction()as s:return copy.deepcopy(s['game'])
    def assert_html_same(self):
        legacy=lambda source,rows,frame:SimpleNamespace(players=rows)
        with patch('werewolf.player_view.public_view',side_effect=legacy):old=self.c.get('/main').data
        seen=[]
        def capture(sender,template,context,**kwargs):
            if 'players'in context:seen.extend(context['players'])
        with template_rendered.connected_to(capture,self.app):new=self.c.get('/main').data
        self.assertEqual(old,new);self.assertTrue(seen);self.assertTrue(all(isinstance(p,PlayerData)for p in seen))
    def test_public_day_and_night_html_exact_and_input_cookie_unchanged(self):
        self.assert_html_same();g=self.game();cookie=self.c.get_cookie('session').value
        self.assert_html_same();self.assertEqual(self.game(),g);self.assertEqual(self.c.get_cookie('session').value,cookie)
        self.assertEqual(self.c.post('/advance',data={'revision':g['revision'],'target':'1','day':'random','night':'random'}).status_code,303)
        self.assert_html_same()
    def test_pending_html_and_roles_complete_stream_match_legacy_rows(self):
        with patch('werewolf.board_flow.RoleState.forecast',return_value=FuturePending('information_set_budget_exceeded')):self.assert_html_same()
        legacy=lambda source,rows,frame:SimpleNamespace(players=rows)
        def events():
            r=self.c.get('/main',headers={'Accept':'application/x-ndjson'},buffered=False);value=[json.loads(x)for x in r.response];r.close();return value
        with patch('werewolf.player_view.public_view',side_effect=legacy):old=events()
        new=events();self.assertEqual([x['event']for x in new],['roles','complete'])
        self.assertEqual([x['html']for x in old],[x['html']for x in new])
    def test_private_roles_pending_empty_envelope_is_preserved(self):
        g=self.game();self.c.post('/advance',data={'revision':g['revision'],'target':'1','day':'random','night':'random'});g=self.game()
        form={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps({'role':'wolf','players':[2],'results':[]})}
        with patch('werewolf.private_adapter.prepared_private_role_rows',return_value={'players':[],'reason':'pending role support'}):
            r=self.c.post('/private-view',data=form,headers={'Accept':'application/x-ndjson'},buffered=False)
            events=[json.loads(x)for x in r.response];r.close()
        self.assertEqual([x['event']for x in events],['roles','complete'])
        self.assertEqual(events[0]['players'],[]);self.assertEqual(events[0]['reason'],'pending role support')
    def test_preview_edit_uses_new_view_but_does_not_save(self):
        g=self.game();seen=[]
        def capture(sender,template,context,**kwargs):
            if 'players'in context:seen.extend(context['players'])
        payload={'claims':['latent']*5,'seers':[],'mediums':[]}
        with template_rendered.connected_to(capture,self.app):
            r=self.c.post('/table-preview',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'request_id':'99','payload':json.dumps(payload)})
        self.assertEqual(r.status_code,200,r.data);self.assertEqual(r.json['request_id'],'99');self.assertEqual(self.game(),g)
        self.assertTrue(all(isinstance(p,PlayerData)for p in seen))

if __name__=='__main__':unittest.main()