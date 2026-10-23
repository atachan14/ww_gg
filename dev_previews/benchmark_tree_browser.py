"""Actual isolated browser timings for the same projection-only adapter baseline."""
import argparse,runpy
from dev_previews.benchmark_tree_projection import historical
from werewolf import navigation_tree,navigation_current
p=argparse.ArgumentParser();p.add_argument('--baseline');args=p.parse_args()
if args.baseline:
 old=historical(args.baseline,'navigation_tree')
 navigation_tree._presentation_source=old._summary.__globals__['_presentation_source']
 navigation_tree.NavigationTree._binding=old._binding
 navigation_current.NavigationCurrent.__init__=historical(args.baseline,'navigation_current').__init__
print('adapter='+str(args.baseline or 'working'),flush=True)
runpy.run_path('dev_previews/verify_max_hidden_counts.py',run_name='__main__')
