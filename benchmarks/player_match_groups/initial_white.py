"""Actual /start -> /table-publish -> BoardData -> prepared prior fixture."""
import copy,json
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Strategy
from werewolf.player_view import build_public_view,ViewScope,ResultFrame


def prepare(client):
    with client.session_transaction()as session:game=copy.deepcopy(session['game'])
    data=BoardData.from_game(game);roles=data.roles();board=roles.board
    strategy=Strategy(**game['policy'])
    kind,value=prepare_evaluation(game,board,roles.rules,strategy,max_work=1000000,max_seconds=20)
    assert kind=='prior',kind
    state,past=value
    view=build_public_view(data,roles,board,ResultFrame(ViewScope.public(data),'roles'),state=game,event_history=board.history,alive=board.alive,action_values={},by_dawn_values={})
    return data,roles,board,state,past,roles.rules,strategy,view


def publish(client,target=3):
    with client.session_transaction()as session:g=copy.deepcopy(session['game'])
    payload={'claims':['seer']+['latent']*(g['players']-1),'seers':[{'day':1,'reporter':1,'target':target,'color':'white'}],'mediums':[]}
    response=client.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
    assert response.status_code==200,response.data


def initial_white_source(n=5,wolves=1,target=3,*,return_client=False):
    app=create_app({'TESTING':True,'SECRET_KEY':'matching-initial-white','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True})
    client=app.test_client()
    response=client.post('/start',data={'citizens':str(n-wolves-1),'seers':'1','wolves':str(wolves),'day':'random','night':'random','fake_reports':'random','initial_seer':'random_white'})
    assert response.status_code==303,response.data
    publish(client,target)
    result=prepare(client)
    assert result[6].fake_reports=='random'
    return (result,client)if return_client else result
