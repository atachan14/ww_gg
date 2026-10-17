import copy,json,unittest
from dataclasses import FrozenInstanceError,replace
from unittest.mock import patch
from flask import template_rendered
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.player_view import ViewScope,ResultFrame,PublicIndex,public_view,personal_view

class PlayerViewTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'player-read-view','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':2})
        self.c=self.app.test_client();self.start()
    def start(self,seers=0):
        self.assertEqual(self.c.post('/start',data={'citizens':str(4-seers),'seers':str(seers),'wolves':'1','day':'random','night':'random'}).status_code,303)
    def game(self):
        with self.c.session_transaction()as s:return copy.deepcopy(s['game'])
    def rows(self,**kwargs):
        seen=[]
        def capture(sender,template,context,**extra):
            if 'players'in context:seen.append(copy.deepcopy(context['players']))
        with template_rendered.connected_to(capture,self.app):
            r=self.c.get('/main',**kwargs)
            self.assertEqual(r.status_code,200)
            if kwargs.get('headers',{}).get('Accept')=='application/x-ndjson':list(r.response);r.close()
        return seen[-1]
    def build(self,stage='complete',request='1'):
        rows=self.rows();data=BoardData.from_game(self.game());frame=ResultFrame(ViewScope.public(data),stage,request)
        return data,rows,frame,public_view(data,rows,frame)
    def table(self,claims,seers):
        g=self.game();r=self.c.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps({'claims':claims,'seers':seers,'mediums':[]})})
        self.assertEqual(r.status_code,200,r.data)
    def test_every_existing_public_field_and_readonly_snapshot(self):
        data,rows,frame,view=self.build();before=copy.deepcopy(self.game())
        self.assertEqual([p.to_legacy_row()for p in view.players],rows)
        self.assertEqual(view.by_id(1).name,rows[0]['name']);self.assertEqual(view.by_id(1).co,rows[0]['claim'])
        self.assertEqual(view.by_id(2).by_dawn,rows[1]['by_dawn'])
        with self.assertRaises(FrozenInstanceError):view.by_id(1).current_co='wolf'
        with self.assertRaises(TypeError):view.by_id(1).legacy['alive']=False
        with self.assertRaises(TypeError):view.by_id(1).extra_probabilities['seer']=1
        exported=view.by_id(1).to_legacy_row();exported['extra_probabilities']['seer']=99
        self.assertEqual(view.by_id(1).to_legacy_row(),rows[0]);self.assertEqual(self.game(),before)
        rows[0]['name']='changed';self.assertNotEqual(view.by_id(1).name,'changed')
    def test_view_construction_does_not_recalculate_or_persist(self):
        data,rows,frame,view=self.build();before=data.inputs
        with patch.object(BoardData,'roles',side_effect=AssertionError('view calculated')):
            other=public_view(data,rows,frame)
        self.assertEqual(other.players,view.players);self.assertEqual(data.inputs,before)
        self.assertNotIn('player_view',data.to_game());self.assertNotIn('PlayerData',data.to_game())
    def test_publication_reverse_index_correction_withdraw_and_order(self):
        self.start(1);claims=['seer']+['latent']*4
        self.table(claims,[{'day':1,'reporter':1,'target':3,'color':'white'}])
        data,rows,frame,old=self.build();before=copy.deepcopy(self.game())
        d=old.by_id(3).received_claims[0]
        self.assertEqual((d.player,d.target,d.acquired_day,d.published_day),(1,3,1,1))
        self.assertEqual(d.event['kind'],'seer');self.assertIs(d,old.by_id(1).declarations[-1])
        self.assertTrue(all(a.order<b.order for a,b in zip(old.public_index.events,old.public_index.events[1:])))
        self.table(claims,[{'day':1,'reporter':1,'target':4,'color':'white'}])
        _,_,newframe,new=self.build()
        self.assertEqual(new.by_id(3).received_claims,());self.assertEqual(new.by_id(4).received_claims[0].target,4)
        self.assertEqual(old.by_id(3).received_claims[0].target,3)
        self.assertEqual(old.by_id(1).metric('action',current_frame=newframe).status,'stale')
        self.assertNotEqual(before,self.game())
        self.table(['latent']*5,[]);_,_,_,withdrawn=self.build()
        self.assertEqual(withdrawn.by_id(1).co,'latent');self.assertTrue(all(not p.received_claims for p in withdrawn.players))
        self.assertTrue(any(d.event.get('action')=='withdraw'for d in withdrawn.by_id(1).declarations))
    def test_old_results_request_generation_and_pending_are_distinct(self):
        data,rows,frame,view=self.build()
        self.assertEqual(view.by_id(1).metric('action').status,'complete')
        self.assertEqual(view.by_id(1).metric('action',current_frame=replace(frame,request_id='new')).status,'stale')
        pending=public_view(data,rows,replace(frame,stage='pending',reason='work'))
        self.assertEqual(pending.by_id(1).metric('action').status,'pending');self.assertIsNone(pending.by_id(1).metric('action').value)
        self.assertEqual(pending.by_id(1).metric('wolf_probability').status,'complete')
        self.assertEqual(public_view(data,rows,replace(frame,stage='invalid')).by_id(1).metric('action').status,'invalid')
        changed=data.updated(revision=data.to_game()['revision']+1)
        with self.assertRaises(ValueError):public_view(changed,rows,frame)
    def test_private_rows_round_trip_and_switch_without_public_mutation(self):
        g=self.game();self.assertEqual(self.c.post('/advance',data={'revision':g['revision'],'target':'1','day':'random','night':'random'}).status_code,303)
        data,rows,frame,public=self.build();before=copy.deepcopy(self.game());public_before=[p.to_legacy_row()for p in public.players]
        results=[];payload={'role':'wolf','players':[2],'results':results}
        r=self.c.post('/private-view',data={'revision':before['revision'],'board_id':before['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(r.status_code,200,r.data);private_rows=r.json['players']
        scope=public.scope.personal('wolf',(2,),payload);private_frame=ResultFrame(scope,'complete','private-1')
        private=personal_view(public,private_rows,private_frame)
        self.assertEqual([p.to_legacy_row()for p in private.players],private_rows)
        self.assertIs(private.public_index,public.public_index)
        self.assertEqual(public_before,[p.to_legacy_row()for p in public.players]);self.assertEqual(before,self.game())
        self.assertNotEqual(private.scope,public.scope)
        self.assertEqual(private.by_id(2).metric('probabilities',current_frame=frame).status,'stale')
        self.assertEqual(public.by_id(2).metric('wolf_probability',current_frame=private_frame).status,'stale')
        with self.assertRaises(ValueError):public_view(data,private_rows,private_frame)
        with self.assertRaises(ValueError):personal_view(public,private_rows,frame)
        injected=copy.deepcopy(rows);injected[0]['acquisitions']=[{'secret':'not public'}]
        with self.assertRaises(ValueError):public_view(data,injected,frame)
    def test_actual_seer_secret_is_not_a_received_public_claim(self):
        self.start(1);g=self.game()
        self.assertEqual(self.c.post('/advance',data={'revision':g['revision'],'target':'2','day':'random','night':'random'}).status_code,303)
        data,rows,frame,public=self.build();g=self.game()
        payload={'role':'seer','players':[1],'results':[{'day':1,'target':3,'color':'white'}]}
        response=self.c.post('/private-view',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(response.json['acquisitions'])
        private=personal_view(public,response.json['players'],ResultFrame(public.scope.personal('seer',(1,),payload),'complete','seer'))
        self.assertEqual(private.by_id(1).probabilities['seer'],'1')
        self.assertFalse(public.by_id(3).received_claims)
        self.assertEqual([p.to_legacy_row()for p in public.players],rows)
        self.assertEqual(public.by_id(1)['name'],rows[0]['name'])
        self.assertEqual(self.game(),g)
    def test_roles_stream_rows_preserve_pending_values_without_zero_fill(self):
        rows=[]
        def capture(sender,template,context,**extra):
            if 'players'in context:rows.append(copy.deepcopy(context['players']))
        with template_rendered.connected_to(capture,self.app):
            r=self.c.get('/main',headers={'Accept':'application/x-ndjson'},buffered=False);events=[json.loads(x)for x in r.response];r.close()
        self.assertEqual(events[0]['event'],'roles')
        data=BoardData.from_game(self.game());frame=ResultFrame(ViewScope.public(data),'roles','stream')
        view=public_view(data,rows[0],frame)
        self.assertEqual([p.to_legacy_row()for p in view.players],rows[0])
        self.assertEqual(view.by_id(1).metric('action').status,'pending');self.assertIsNone(view.by_id(1).metric('action').value)
    def test_back_past_edit_regenerates_index_without_child_leak(self):
        self.app.config['DAWN_BOARD_PREVIEW']=False
        self.start(1);claims=['seer']+['latent']*4
        self.table(claims,[{'day':1,'reporter':1,'target':3,'color':'white'}])
        def advance(target):
            g=self.game();self.assertEqual(self.c.post('/advance',data={'revision':g['revision'],'target':str(target),'day':'random','night':'random'}).status_code,303)
        def back():
            g=self.game();self.assertEqual(self.c.post('/back',data={'revision':g['revision']}).status_code,303)
        advance(2);advance(3)
        self.table(claims,[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':2,'reporter':1,'target':4,'color':'white'}])
        _,_,childframe,child=self.build()
        self.assertTrue(child.by_id(4).received_claims)
        back();back();_,_,rootframe,root=self.build()
        self.assertFalse(root.by_id(4).received_claims)
        self.assertEqual(root.by_id(1).metric('action',current_frame=childframe).status,'stale')
        self.table(claims,[{'day':1,'reporter':1,'target':4,'color':'white'}])
        _,_,_,edited=self.build();self.assertFalse(edited.by_id(3).received_claims)
        self.assertEqual(root.by_id(3).received_claims[0].target,3)
    def test_manual_pending_and_missing_are_not_zero_or_unsupported(self):
        from werewolf.seer_manual import ManualPending
        data,rows,frame,view=self.build()
        rows[0]['wolf_probability']=ManualPending('evidence pending')
        rows[0]['action']=None
        rows[0]['extra_probabilities']['seer']=ManualPending('nested pending')
        current=public_view(data,rows,frame).by_id(1)
        self.assertEqual(current.metric('wolf_probability').status,'pending')
        self.assertEqual(current.metric('wolf_probability').reason,'evidence pending')
        self.assertIsNone(current.metric('wolf_probability').value)
        self.assertEqual(current.metric('action').status,'missing')
        self.assertEqual(current.metric('extra_probabilities').status,'pending')
        self.assertEqual(current.to_legacy_row(),rows[0])
    def test_legacy_index_preserves_unknown_order_and_does_not_mutate_input(self):
        self.start(1);g=self.game();g.pop('public_log',None)
        g['claims']=['seer']+['latent']*4
        g['seer_inputs']=[{'day':1,'reporter':1,'target':3,'color':'white'}]
        before=copy.deepcopy(g);data=BoardData.from_game(g);index=PublicIndex.from_board(data)
        self.assertEqual(index.current_co[0],'seer');self.assertEqual(index.received[2][0].target,3)
        self.assertIsNone(index.received[2][0].order)
        self.assertEqual(g,before);self.assertEqual(data.to_game(),before)
    def test_personal_evidence_digest_and_new_game_lifetime(self):
        data,rows,frame,view=self.build()
        a=view.scope.personal('seer',(1,),[{'day':1,'target':2,'color':'white'}]);b=view.scope.personal('seer',(1,),[{'day':1,'target':3,'color':'white'}])
        self.assertNotEqual(a,b)
        cold=BoardData.from_game(data.to_game());self.assertNotEqual(ViewScope.public(cold),view.scope)
        with self.assertRaises(ValueError):public_view(cold,rows,frame)

if __name__=='__main__':unittest.main()