"""Short seven-player baseline/OFF/fallback check; never a heavy benchmark."""
import sys,json,subprocess,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Strategy
from werewolf.player_view import ViewScope,ResultFrame,build_public_view
from werewolf.model_a_public import public_forecast
from werewolf.match_groups import make_engine
from werewolf.calculation_budget import budget_stop,reset_diagnostics
from werewolf.seer_future_uniform import FuturePending

def child(mode):
    cases=json.loads(subprocess.check_output(['git','show','cb8ea84:benchmarks/browser_backend_qa/cases.json'],cwd=ROOT))
    g=cases['heavy-seven']['game'];data=BoardData.from_game(g);roles=data.roles();b=roles.board;strategy=Strategy(**g['policy'])
    kind,prepared=prepare_evaluation(g,b,roles.rules,strategy,max_work=100000,max_seconds=3);assert kind=='prior'
    s,past=prepared
    view=build_public_view(data,roles,b,ResultFrame(ViewScope.public(data),'roles'),state=g,event_history=b.history,alive=b.alive,action_values={},by_dawn_values={})
    active=make_engine(b,s,past,roles.rules,strategy,enabled=mode=='requested',view=view).grouping
    call=public_forecast
    if mode=='frozen03':
        code=subprocess.check_output(['git','show','03e4e31:werewolf/model_a_public.py'],cwd=ROOT).decode('utf8')
        module=types.ModuleType('_ww_frozen03_public');module.__package__='werewolf';exec(compile(code,'03e4e31/model_a_public.py','exec'),module.__dict__);call=module.public_forecast
    reset_diagnostics();kw=dict(max_work=1000,max_seconds=2)
    if mode=='requested':kw.update(match_groups=True,match_view=view)
    result=call(b,s,past,roles.rules,strategy,**kw)
    rows=[{k:str(v)for k,v in roles.probabilities(i).items()}for i in range(1,8)]
    assert rows[0]['seer']==rows[0]['wolf']=='1/2';assert rows[1]==rows[0]
    assert rows[2]['medium']=='1';assert rows[3]['villager']=='1'
    assert all(rows[i]['wolf']=='1/3'and rows[i]['villager']=='2/3'for i in(4,5,6))
    assert not active;assert isinstance(result,FuturePending)
    return dict(mode=mode,roles=rows,status='pending',reason=result.reason,budget_kind=(budget_stop()or{}).get('kind'),group_active=active,limits=kw if mode!='requested'else dict(max_work=1000,max_seconds=2),note='exact frozen03 entrypoint with unchanged numerical kernels; no full win calculation')

if __name__=='__main__':
    if '--child'in sys.argv:print(json.dumps(child(sys.argv[2])));raise SystemExit()
    rows=[]
    for mode in('frozen03','off','requested'):
        p=subprocess.run([sys.executable,'-B',__file__,'--child',mode],cwd=ROOT,capture_output=True,text=True,encoding='utf8',timeout=10)
        if p.returncode:raise RuntimeError(p.stderr+p.stdout)
        rows.append(json.loads(p.stdout))
    for r in rows[1:]:
        for key in('roles','status','reason','budget_kind','group_active'):assert r[key]==rows[0][key],key
    (ROOT/'benchmarks/player_view_refactor/final-seven-short.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf8');print(json.dumps(dict(roles_equal=True,pending_equal=True,budget_kind=rows[0]['budget_kind'],limits=rows[0]['limits'],group_active=False)))