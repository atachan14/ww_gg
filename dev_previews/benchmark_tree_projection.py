"""Isolated cold/warm projection benchmark; optional historical adapter comparison.

No normal HTTP server or saved game is read. Historical adapters use the same
current evaluator/fixture, isolating presentation work from policy changes.
"""
import argparse,json,subprocess,types
from hashlib import sha256
from time import perf_counter
from fractions import Fraction
from tests.test_max_hidden_count_records import MaxHiddenCountRecordsTests
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.calculation_budget import calculation_budget

def historical(ref,file):
 source=subprocess.check_output(['git','show',ref+':werewolf/'+file+'.py'],text=True,encoding='utf-8')
 module=types.ModuleType('werewolf._benchmark_'+file);module.__package__='werewolf'
 exec(compile(source,'historical/'+file+'.py','exec'),module.__dict__)
 return getattr(module,'NavigationTree' if file=='navigation_tree' else 'NavigationCurrent')

def run(baseline=None):
 Tree=historical(baseline,'navigation_tree') if baseline else NavigationTree
 Current=historical(baseline,'navigation_current') if baseline else NavigationCurrent
 rows=[]
 def phase(name,fn):
  start=perf_counter();result=fn();rows.append(dict(phase=name,seconds=round(perf_counter()-start,4)));return result
 with calculation_budget(4000000,max_seconds=120):
  fixture=MaxHiddenCountRecordsTests();doc=phase('cold-document',fixture.document)
  assert phase('initial-value',lambda:doc.game.node.forecast().village_win)==Fraction(8,35)
  phase('representative-six',lambda:doc.game.action(6));tree=Tree(doc)
  phase('first-root-response',lambda:tree.read(expand=True))
  night=phase('first-night-response',lambda:tree.read(tree.current_key(),True))
  phase('repeat-night-response',lambda:tree.read(tree.current_key(),True))
  wire=phase('night-json-serialization',lambda:json.dumps(night))
  key=next(row['node'] for row in fixture.leaves(night['night_stages']) if not night['items'][row['node']]['winner'])
  phase('select-day2',lambda:tree.select(key))
  current=phase('day2-current-projection',lambda:Current(doc.game))
  repeat=phase('day2-current-repeat',lambda:Current(doc.game))
  assert current.source==repeat.source
  assert doc.game.history.state(doc.game.history.root).node.forecast().village_win==Fraction(8,35)
  for row in rows:print(json.dumps(dict(adapter=baseline or 'working',**row)),flush=True)
  print(json.dumps(dict(adapter=baseline or 'working',night_items=len(night['items']),night_json_bytes=len(wire.encode()),night_sha256=sha256(wire.encode()).hexdigest(),value='8/35')),flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--baseline');run(parser.parse_args().baseline)
