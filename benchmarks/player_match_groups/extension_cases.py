"""Actual API cases and ordinary prior preparation, including max policies."""
import copy,json
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Strategy
from werewolf.player_view import build_public_view,ViewScope,ResultFrame


def prepare_game(game):
    data=BoardData.from_game(game);roles=data.roles();b=roles.board;strategy=Strategy(**game['policy'])
    kind,result=prepare_evaluation(game,b,roles.rules,strategy,max_work=1000000,max_seconds=20)
    if kind!='prior':raise ValueError('Expected complete prior, got '+kind)
    s,past=result
    view=build_public_view(data,roles,b,ResultFrame(ViewScope.public(data),'roles'),state=game,event_history=b.history,alive=b.alive,action_values={},by_dawn_values={})
    return data,roles,b,s,past,roles.rules,strategy,view


def fixture(n=5,wolves=1,mediums=0,day='random',night='random',fake='random',target=None):
    app=create_app({'TESTING':True,'SECRET_KEY':'extension-acceptance','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True})
    client=app.test_client();target=target or(4 if mediums else 3)
    response=client.post('/start',data={'citizens':str(n-wolves-mediums-1),'mediums':str(mediums),'seers':'1','wolves':str(wolves),'day':day,'night':night,'fake_reports':fake,'initial_seer':'random_white'})
    assert response.status_code==303,response.data
    publish(client,target,mediums)
    return client,game_of(client)


def game_of(client):
    with client.session_transaction()as session:return copy.deepcopy(session['game'])


def publish(client,target,mediums=0,withdraw=False):
    game=game_of(client);n=game['players']
    claims=['latent']*n
    if not withdraw:
        claims[0]=claims[1]='seer'
        if mediums:claims[2]='medium'
    payload={'claims':claims,'seers':[]if withdraw else[{'day':1,'reporter':p,'target':target,'color':'white'}for p in(1,2)],'mediums':[]}
    response=client.post('/table-publish',data={'revision':game['revision'],'board_id':game['public_log']['board_id'],'payload':json.dumps(payload)})
    assert response.status_code==200,response.data
