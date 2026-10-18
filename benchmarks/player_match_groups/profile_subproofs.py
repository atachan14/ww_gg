"""Save completed child certificates, independently check every selected deviation.
No partial root result is imported or treated as a policy certificate.
"""
import json,time,hashlib
from pathlib import Path
from tests.test_root_guard_max import RootGuardMaxTests
from werewolf.seer_manual import replay
from werewolf.exact import Strategy
from werewolf.root_secret_flow import prepare_root_entry
from werewolf.wolf_profile_certificate import WolfProfileResolver,FixedPublicWolfProfile,wolf_candidate_profile
from werewolf.candidate_policy import CandidateRules
from werewolf.actor_information import wolf_information_groups
from werewolf.calculation_budget import calculation_budget
from .checkpoint_audit import encode

def run():
 rows=[]
 for n in(5,6):
  g=RootGuardMaxTests().game(players=n);g['policy']['day']=g['history'][0]['policy']['day']='max';rules,p=replay(g);strategy=Strategy(**g['policy']);root=prepare_root_entry(g,p.board,rules,strategy)
  resolver=WolfProfileResolver(rules,strategy,max_work=100000,max_seconds=2);started=time.perf_counter();result=resolver.resolve(root.public,root.public_law)
  slices=[dict(status=result.status,children=len(resolver.cache),certificate_hits=resolver.certificate_cache_stats['hits'])]
  if n==6 and result.selected is None:
   # Resume with the SAME validated completed child cache, not a longer cold run.
   previous=len(resolver.cache)
   result=resolver.resolve(root.public,root.public_law)
   slices.append(dict(status=result.status,children=len(resolver.cache),new_complete_children=len(resolver.cache)-previous,certificate_hits=resolver.certificate_cache_stats['hits']))
  completed=list(resolver.cache.items());small=[x for x in completed if len(x[0][0].alive)<=3]
  if result.selected is not None:small.insert(0,((root.public,root.public_law,()),result))
  small.sort(key=lambda x:not any(v for i,row in x[1].selected.scores for t,v in row))
  checks=[]
  for (b,s,past),cert in small[:2]:
   groups={info:law for info,mass,law in wolf_information_groups(s)};candidates=CandidateRules(b,s,past,rules,strategy);verified=[]
   with calculation_budget(1000000,max_seconds=12):
    for info,row in cert.selected.scores:
     for target,score in row:
      profile=wolf_candidate_profile(cert.selected.profile,info,target,rules=candidates)
      fresh=FixedPublicWolfProfile(b,s,past,rules,strategy,profile,resolver=WolfProfileResolver(rules,strategy,canonical_certificates=False))
      actual=fresh.act(b,s,past,target,groups[info],None)
      assert actual==score,(n,info,target,actual,score)
      verified.append((info,target,score))
   checks.append(encode(dict(board=b,state=s,past=past,certificate=cert,verified_rows=verified,all_deviations_match=True)))
  assert checks,'No completed small child proof within bounded probe'
  rows.append(encode(dict(players=n,resume_slices=slices,root_certificate=result if result.selected is not None else None,root_status=result.status,root_reason=result.reason,root_selected=result.selected is not None,root_cached=(root.public,root.public_law,())in resolver.cache,complete_child_certificates=len(completed),checkpoint_children=checks,seconds=time.perf_counter()-started,branch_stats=resolver.branch_stats,acquisition_stats=resolver.acquisition_stats,canonical_certificate_stats=resolver.certificate_cache_stats)))
  Path('benchmarks/player_match_groups/profile-child-checkpoints.json').write_text(json.dumps(dict(schema='review-only-complete-context-v1',source_sha256=hashlib.sha256(json.dumps([(str(p),hashlib.sha256(p.read_bytes()).hexdigest())for p in sorted(Path('werewolf').glob('*.py'))]).encode()).hexdigest(),rules=encode(rules),strategy=encode(strategy),automatic_cache_import=False,rows=rows),indent=2)+'\n')
  print(json.dumps(dict(players=n,root_status=result.status,completed_children=len(completed),checked_children=len(checks),seconds=time.perf_counter()-started)),flush=True)
if __name__=='__main__':run()
