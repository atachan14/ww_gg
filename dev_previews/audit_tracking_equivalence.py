"""Bounded current/baseline tracking comparison, without modifying a checkout."""
import argparse,hashlib,importlib.abc,importlib.util,io,json,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
parser=argparse.ArgumentParser();parser.add_argument('--baseline');parser.add_argument('--bridge',action='store_true');args=parser.parse_args()
if args.baseline:
 archive=subprocess.check_output(['git','archive',args.baseline,'werewolf'],cwd=ROOT)
 with tarfile.open(fileobj=io.BytesIO(archive)) as tar:sources={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile() and m.name.endswith('.py')}
 class Snapshot(importlib.abc.MetaPathFinder,importlib.abc.Loader):
  def find_spec(self,fullname,path=None,target=None):
   relative=fullname.replace('.','/')+'.py'
   if relative in sources:return importlib.util.spec_from_loader(fullname,self)
   if fullname.startswith('werewolf.') and relative not in sources:raise ImportError('Not present in baseline: '+fullname)
  def create_module(self,spec):return None
  def exec_module(self,module):
   relative=module.__name__.replace('.','/')+'.py';module.__file__=str(ROOT/relative);exec(compile(sources[relative],module.__file__,'exec'),module.__dict__)
 sys.meta_path.insert(0,Snapshot())
if args.bridge:
 from benchmarks.player_match_groups.cut_out_six_registry_fixture import setup
 from benchmarks.player_match_groups.cut_out_six_source_bridge import issue
 from werewolf.calculation_budget import calculation_budget
 with calculation_budget(300000,max_seconds=15):
  rows=[]
  for target in (2,4):
   _,registry=setup(day2_target=target);answer=issue(registry)
   rows.append(dict(target=target,problem=getattr(registry.problem,'reason',None),answer=type(answer).__name__,reason=getattr(answer,'reason',None)))
  print(json.dumps(dict(baseline=args.baseline or 'working',bridge=rows)))
 raise SystemExit(0)
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_budget import calculation_budget
with calculation_budget(250000,max_seconds=20):
 graph=case(5,'single');plain=ClosedCalculation(graph.data);grouped=ClosedCalculation(graph.data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
 a,b=plain.root.read(),grouped.root.read();cold=independent_cold(graph,grouped.root.export_request())
 fields=('public','public_state','past','private','observer','physical')
 print(json.dumps(dict(baseline=args.baseline or 'working',plain_grouped=a==b,grouped_cold=b==cold,fields_equal={f:getattr(a,f)==getattr(b,f)==getattr(cold,f) for f in fields},tracking=[s.public_state.tracked for s in (a,b,cold)],hypotheses_equal=a.public_state.hypotheses==b.public_state.hypotheses==cold.public_state.hypotheses,rosters_equal=a.public_state.rosters==b.public_state.rosters==cold.public_state.rosters)))
