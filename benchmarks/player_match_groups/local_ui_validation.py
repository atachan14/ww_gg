"""Actual local UI stream acceptance against pre-integration complete Table."""
import json,re,time,copy
from pathlib import Path
from unittest.mock import patch
from app import create_app
from werewolf.board_flow import RoleState
from werewolf.player_view import build_public_view,ViewScope,ResultFrame
from werewolf.exact import Values
from .checkpoint_audit import encode

def run():
    source=json.loads(Path('benchmarks/player_match_groups/actual-seven-extended-retirement.json').read_text(encoding='utf-8'))
    app=create_app({'TESTING':True,'SECRET_KEY':'local-ui-seven','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'EXACT_FUTURE_REUSE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':60})
    c=app.test_client()
    with c.session_transaction()as session:session['game']=source['game']
    original=RoleState.forecast;tables=[]
    def capture(self,**kwargs):
        result=original(self,**kwargs);game=self.owner.to_game()
        view=build_public_view(self.owner,self,self.board,ResultFrame(ViewScope.public(self.owner),'complete'),state=game,event_history=self.board.history,alive=self.board.alive,action_values={p:Values(v,1-v)for p,v in result.action_values},by_dawn_values=dict(result.by_dawn_values))
        tables.append(encode([p.to_legacy_row()for p in view.players]));return result
    started=time.perf_counter()
    with patch.object(RoleState,'forecast',capture):response=c.get('/main',headers={'Accept':'application/x-ndjson'},buffered=True)
    events=[json.loads(line)for line in response.data.decode().splitlines()]
    assert not any(e['event']=='error'for e in events)
    rendered=[e for e in events if e['event']in('roles','complete')]
    assert[e['event']for e in rendered]==['roles','complete']
    differences=[dict(player=i+1,field=k,expected=old.get(k),actual=new.get(k))for i,(old,new)in enumerate(zip(source['result']['table'],tables[0]))for k in old.keys()|new.keys()if old.get(k)!=new.get(k)]
    Path('.artifacts').mkdir(exist_ok=True)
    Path('.artifacts/local-ui-seven-row-differences.json').write_text(json.dumps(differences,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'row_differences':differences}),flush=True)
    assert not differences
    assert re.search(r'id="village-rate"[^>]*data-fraction="17/36"',rendered[-1]['html'])
    record=dict(reference='8f7455d actual-seven-extended-retirement.json complete local prototype',status=response.status_code,seconds=time.perf_counter()-started,roles_first=True,all_table_rows_match_preintegration_reference=True,terminal='17/36',execution='actual Flask NDJSON/position worker and BoardData runtime',event_types=[e['event']for e in events])
    Path('benchmarks/player_match_groups/local-ui-seven-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    return record
if __name__=='__main__':print(json.dumps(run()),flush=True)
