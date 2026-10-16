"""Compare exact root/public-secret preparation, separately from timed requests."""
import argparse,importlib,importlib.util,json,pkgutil,subprocess,sys
from pathlib import Path
from board_b_benchmark import ROOT,BUDGET,canonical,digest


def worker(a):
 sys.path.insert(0,a.tree)
 import werewolf
 for m in pkgutil.iter_modules(werewolf.__path__):importlib.import_module('werewolf.'+m.name)
 from werewolf.exact import Strategy
 spec=importlib.util.spec_from_file_location('joint_oracle',ROOT/'tests/fixtures/board_replay_v051.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 cases=json.loads(Path(a.cases).read_text(encoding='utf-8'));rows={}
 for name,case in cases.items():
  game=case['game'];strategy=Strategy(**game['policy'])
  if a.version=='new':
   from werewolf.board_flow import BoardData
   from werewolf.board_roles import prepare_evaluation
   roles=BoardData.from_game(game).roles();rules,progress=roles.replay_result
   kind,value=prepare_evaluation(game,progress.board,rules,strategy,**BUDGET)
  else:
   from werewolf.seer_manual import replay
   from werewolf.root_secret_flow import prepare_root_entry
   from werewolf.information_set_forecast import InformationSetForecast
   from werewolf.public_prior import prepare_public_prior
   from werewolf.guard_model import scope_reason
   from werewolf.seer_future_uniform import FuturePending
   rules,progress=replay(game) if game.get('seer_mode')=='information-fixed-v1' else oracle.reconstruct_saved(game)
   b=progress.board;value=prepare_root_entry(game,b,rules,strategy,**BUDGET)
   if value is not None:kind='root'
   else:
    reason=scope_reason(b,rules,strategy,b.guard_prior_roster is not None or b.day==1)
    if reason:kind,value='pending',FuturePending(reason)
    elif InformationSetForecast(rules,strategy).exchangeable(b):kind,value='exchangeable',None
    else:kind,value='prior',prepare_public_prior(game,b,rules,track_live_seers=strategy.disclosure_for('seer')=='all',max_work=BUDGET['max_work'])
  own=None
  if case['view']=='private':
   from werewolf.private_view import condition_private
   v=case['private'];own=condition_private(progress.board,v['role'],v['players'],v['results'],rules=rules)
  semantic=canonical({'kind':kind,'public_and_secret_joint':value,'own_observations':own})
  rows[name]={'semantic':semantic,'digest':digest(semantic)}
 Path(a.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
 q=s.add_parser('run');q.add_argument('--snapshots',required=True);q.add_argument('--output',required=True);q.add_argument('--cases',default=str(ROOT/'benchmarks/board_b_cases.json'))
 q=s.add_parser('worker');q.add_argument('--tree',required=True);q.add_argument('--output',required=True);q.add_argument('--cases',required=True);q.add_argument('--version',required=True)
 a=p.parse_args()
 if a.command=='worker':worker(a);return
 out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);versions={}
 for v in ('old','new'):
  target=out/(v+'.json')
  subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'worker','--tree',str(Path(a.snapshots).resolve()/v),'--cases',str(Path(a.cases).resolve()),'--version',v,'--output',str(target)],check=True,timeout=150)
  versions[v]=json.loads(target.read_text(encoding='utf-8'))
 failures=[k for k in versions['old'] if versions['old'][k]['digest']!=versions['new'][k]['digest']]
 result={'cases':list(versions['old']),'failures':failures,'versions':versions}
 (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'cases':result['cases'],'failures':failures}),flush=True)
 if failures:raise AssertionError(failures)
if __name__=='__main__':main()
