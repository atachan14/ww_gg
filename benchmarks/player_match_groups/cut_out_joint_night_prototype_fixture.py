"""Small exact labelled oracle for the unconnected joint night prototype."""
from dataclasses import replace
from fractions import Fraction as F
from collections import defaultdict
from unittest.mock import patch
from pathlib import Path
import json
from .cut_out_joint_night_prototype import *
from .cut_out_candidate_context_fixture import zero_legacy


def audit(executed=3,weights=None):
 from werewolf.actor_information import wolf_information_groups
 from werewolf.seer_acquisition import normalize
 cap=make_case(executed,weights);x=cap.source
 stack,mocks=zero_legacy();actual={};expected={};generated=0;labelled=0
 with stack,calculation_budget(500000,max_seconds=5):
  # The actual producer cannot enumerate literal information sets/actions or
  # invoke a permutation-matching oracle. Label expansion is output readback.
  with patch('werewolf.actor_information.wolf_information_groups',side_effect=AssertionError('no literal info product')),patch('benchmarks.player_match_groups.cut_out_day_night.moved_law',side_effect=AssertionError('no permutation matching')):
   orbits=produce(cap)
  representative_leaves=0
  for orbit in orbits:
   leaves=simulate(cap,orbit.roster,orbit.target);generated+=1;representative_leaves+=len(leaves)
   for roster,target,mapping in labels(cap,orbit):
    labelled+=1
    for leaf in leaves:
     child=restore(leaf,mapping);key=(roster,target,child)
     assert key not in actual
     actual[key]=(orbit.public_mass/orbit.multiplicity*child.q,orbit.physical_mass/orbit.multiplicity*child.p)
  qgroups={info:mass for info,mass,_ in wolf_information_groups(x.public_state)}
  # Explicit old labelled traversal is ONLY the test oracle.
  e=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,exact_renaming=False)
  raw_generations=0
  for info,pm,own in wolf_information_groups(x.private):
   qm=qgroups[info]
   policy=dict(e.wolf_policy(x.public,x.public_state,x.past,info.initial_roster,info.attacks))
   for target,mass in policy.items():
    raw_generations+=1
    for leaf in simulate(cap,info.initial_roster,target):
     key=(info.initial_roster,target,leaf);assert key not in expected
     expected[key]=(qm*mass*leaf.q,pm*mass*leaf.p)
  existing_calls=sum(o.multiplicity//sum(p in x.public.alive and not o.roster&(1<<(p-1)) for p in o.target_block) for o in orbits)
  assert actual==expected
  assert sum((v[0] for v in actual.values()),F())==sum((v[1] for v in actual.values()),F())==1
  # Full labelled probability Table and role/scan/attack/report joint readback.
  tables={k:(probability_table(k[2]),v) for k,v in actual.items()}
  old_tables={k:(probability_table(k[2]),v) for k,v in expected.items()}
  assert tables==old_tables
  action_rows={t:tuple(sum((mass[i] for (roster,target,leaf),mass in actual.items() if target==t),F()) for i in (0,1)) for t in x.public.alive}
  old_rows={t:tuple(sum((mass[i] for (roster,target,leaf),mass in expected.items() if target==t),F()) for i in (0,1)) for t in x.public.alive}
  assert action_rows==old_rows
  corpse_scans=sum(any(a.day==2 and a.target not in leaf.public.alive for h in leaf.private.hypotheses for a in h.acquisitions) for _,_,leaf in actual)
  assert corpse_scans
  assert all(m.call_count==0 for m in mocks)
 return dict(executed=executed,status='exact_local_equal',representative_flow_generations=generated,
  old_labelled_flow_generations=raw_generations,saved_flow_generations=raw_generations-generated,
  existing_grouped_flow_calls=existing_calls,saved_vs_existing_grouped=existing_calls-generated,
  representative_leaf_generations=representative_leaves,labelled_pairs_restored=labelled,labelled_joint_leaves=len(actual),
  Q_P_different=x.public_state!=x.private,Table_probability_rows_equal=True,labelled_action_probability_rows={p:[str(v) for v in values] for p,values in action_rows.items()},complete_role_scan_attack_report_joint_equal=True,
  physical_branch_mass_equal=True,corpse_scan_leaf_cases=corpse_scans,orbit_multiplicities=[o.multiplicity for o in orbits],
  Q_orbit_masses=[str(o.public_mass) for o in orbits],P_orbit_masses=[str(o.physical_mass) for o in orbits],
  canonical_calls=0,CandidateRules_calls=0,full_forecast_values_tested=False)


def negatives():
 from werewolf.seer_acquisition import normalize
 c=make_case();rejected=[]
 def refuse(name,call):
  try:call()
  except Pending:rejected.append(name)
  else:raise AssertionError(name+' accepted')
 refuse('copied_certificate',lambda:produce(replace(c)))
 for key in ('public_state','private'):
  law=getattr(c.source,key);hs=list(law.hypotheses);hs[0]=replace(hs[0],mass=hs[0].mass*2);bad=replace(law,hypotheses=normalize(tuple(hs)))
  refuse('one_sided_'+key,lambda key=key,bad=bad:produce(c,source=replace(c.source,**{key:bad})))
 refuse('asymmetric_P_pair_weight',lambda:make_case(3,(F(2,3),F(1,3))))
 refuse('nonexact_weights',lambda:make_case(1,(.5,.5)))
 refuse('unsupported_history',lambda:make_case(2))
 original=c.registry.engine.baseline
 object.__setattr__(c.registry.engine,'baseline',replace(original,strategy=replace(original.strategy,night='max')))
 try:refuse('max',lambda:produce(c))
 finally:object.__setattr__(c.registry.engine,'baseline',original)
 refuse('illegal_self_or_teammate_bite',lambda:simulate(c,17,5))
 refuse('dead_bite_target',lambda:simulate(c,17,3))
 refuse('unknown_roster',lambda:simulate(c,3,4))
 refuse('boolean_prefix',lambda:make_case(True))
 assert len(rejected)==11
 return rejected

if __name__=='__main__':
 result=dict(cases=[audit(),audit(1,(F(2,3),F(1,3)))],rejected=negatives(),scope='standalone first-night uniform transition/probability Table only; no Forecast/UI route')
 Path('benchmarks/player_match_groups/cut-out-joint-night-prototype-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))