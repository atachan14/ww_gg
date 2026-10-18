import os,sys,time,json,hashlib,inspect
sys.path.insert(0,os.getcwd())
from dataclasses import replace
from fractions import Fraction as F
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
from werewolf.local_reuse import reuse_scope
from werewolf.seer_future_uniform import FuturePending
from werewolf.information_set_forecast import Pending
from tests import test_root_guard_max as fixtures
from werewolf.seer_manual import replay,migrate_game
from werewolf.exact import Strategy,replace_worlds
from werewolf.root_secret_flow import prepare_root_entry,step_root_action
from werewolf.wolf_profile_certificate import WolfProfileResolver,FixedPublicWolfProfile,wolf_candidate_profile
from werewolf.actor_information import wolf_information_groups,condition_actor_state
from werewolf.seer_acquisition import normalize,public_worlds
from werewolf.candidate_policy import CandidateRules
from werewolf.policy_choice import uniform_policy
from werewolf.information_set_forecast import InformationSetForecast
from unittest.mock import patch
mode=sys.argv[1]=='on';rows=[]
def step(name,fn):
 start=time.perf_counter()
 try:
  with calculation_budget(500000,max_seconds=4):v=fn()
  if isinstance(v,FuturePending):raise RuntimeError(v.reason)
  rows.append(dict(stage=name,seconds=time.perf_counter()-start,complete=True));print(json.dumps(rows[-1]),flush=True);return v
 except (CalculationBudgetExceeded,Pending,RuntimeError)as e:
  rows.append(dict(stage=name,seconds=time.perf_counter()-start,complete=False,reason=type(e).__name__+':'+str(e)));print(json.dumps(rows[-1]),flush=True);return None
with reuse_scope(mode):
 g=fixtures.RootGuardMaxTests().game(True,players=6);g.update(seers=1,mediums=1,claims=['latent']*6);g['history'][0]['claims']=['latent']*6;g=migrate_game(g)
 rules,p=replay(g);strategy=Strategy(**g['policy']);old=replace(strategy,night='random')
 root=step('owned-root',lambda:prepare_root_entry(g,p.board,rules,strategy))
 morning=step('owned-first-night',lambda:next(b for q,b in step_root_action(root,2,rules,old)if len(b.public.alive)==5))if root else None
 later=step('owned-next-day',lambda:next(b for q,b in step_root_action(morning,2,rules,old)if b.public.phase=='night'))if morning else None
 if later:
  selected=tuple(h for h in later.public_law.hypotheses if h.roles[0]in(1,4)and h.roles[3]in(8,16)and h.roles[2]in(8,16)and h.roles[1]==32)
  state=replace(later.public_law,hypotheses=normalize(selected));board=replace_worlds(later.public,public_worlds(state.hypotheses),wolf_count=None)
  info,mass,group=next(x for x in wolf_information_groups(state)if tuple(a.target for a in x[0].attacks)==(2,))
  groups=wolf_information_groups(state);base=tuple((i,uniform_policy(tuple(t for t in board.alive if not i.initial_roster&(1<<(t-1)))))for i,m,st in groups)
  target=next(t for t in board.alive if not info.initial_roster&(1<<(t-1)));profile=wolf_candidate_profile(base,info,target,rules=CandidateRules(board,state,(),rules,strategy))
  def ref():
   e=FixedPublicWolfProfile(board,state,(),rules,strategy,profile,resolver=WolfProfileResolver(rules,strategy));return InformationSetForecast.act(e,board,state,(),target,group,None)
  value=step('owned-one-full-reference',ref)
  law=condition_actor_state(state,lambda h:h.roles[0]==info.initial_roster);own=replace_worlds(board,law.public_roles,wolf_count=None);owned=tuple((i,q)for i,q in profile if i.initial_roster==info.initial_roster)
  actual=step('owned-one-reduced',lambda:FixedPublicWolfProfile(own,law,(),rules,strategy,owned,resolver=WolfProfileResolver(rules,strategy)).act(own,law,(),target,group,None))
  rows.append(dict(stage='owned-witness',hypotheses=len(state.hypotheses),roles=len(state.public_roles),target=target,reference=None if value is None else str(value),actual=None if actual is None else str(actual)))
 for n in(5,6):
  g=fixtures.RootGuardMaxTests().game(players=n);g['policy']['day']=g['history'][0]['policy']['day']='max';r,p=replay(g);s=Strategy(**g['policy']);root=step('profile-root-'+str(n),lambda:prepare_root_entry(g,p.board,r,s))
  if root:
   resolver=WolfProfileResolver(r,s,max_work=100000,max_seconds=4,max_profiles=3)
   result=step('profile-bounded-'+str(n),lambda:resolver.resolve(root.public,root.public_law))
   if result:rows.append(dict(stage='profile-witness-'+str(n),status=result.status,total=result.total,evaluated=result.evaluated,issues=[i.kind for i in result.issues],cached=(root.public,root.public_law,())in resolver.cache))
print('RESULT '+json.dumps(dict(mode=mode,rows=rows,source={n:hashlib.sha256(inspect.getsource(c).encode()).hexdigest()for n,c in(('FixedPublicWolfProfile',FixedPublicWolfProfile),('owned-test',__import__('tests.test_owned_roster_value_cut',fromlist=['OwnedRosterValueCutTests']).OwnedRosterValueCutTests))})),flush=True)
