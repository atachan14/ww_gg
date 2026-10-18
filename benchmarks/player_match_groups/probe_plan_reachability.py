"""Light reachability probe: HTTP setup, stop at first key, keys only afterward."""
import json,time,re
from pathlib import Path
from unittest.mock import patch
from app import create_app
from werewolf.board_flow import BoardData
from werewolf.board_roles import prepare_evaluation
from werewolf.exact import Strategy
from werewolf.local_reuse import reuse_scope
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.exact_renaming import canonical_key
from werewolf.calculation_budget import calculation_budget
from .general_reuse import GeneralReuseForecast
from .bounded_key_plan import planned_key,KeyReusePlan

class FirstKeyReached(Exception):pass

def fixture(role):
 app=create_app({'TESTING':True,'SECRET_KEY':'key-reachability','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True,'EXACT_FUTURE_REUSE_PREVIEW':True})
 c=app.test_client();fields=dict(citizens='5'if role=='plain'else'0',wolves='1',mediums='5'if role=='medium'else'0',seers='5'if role=='seer'else'0',initial_seer='none',day='random',night='random',fake_reports='random')
 assert c.post('/start',data=fields).status_code==303
 def game():
  with c.session_transaction()as session:return dict(session['game'])
 g=game()
 if role!='plain':
  # Current SystemLog publication API, no session mutation or custom bluff rule.
  payload=dict(claims=[role]*6,seers=[],mediums=[])
  response=c.post('/table-publish',data=dict(revision=str(g['revision']),board_id=g['public_log']['board_id'],payload=json.dumps(payload)))
  assert response.status_code==200,(response.status_code,re.findall(r'class="[^"]*error[^"]*"[^>]*>([^<]*)',response.get_data(as_text=True)))
  g=game()
 return app,c,g

def run():
 rows=[]
 for role in('plain','medium','seer'):
  app,c,g=fixture(role);data=BoardData.from_game(g);roles=data.roles();b=roles.board;strategy=Strategy(**g['policy']);captured=[]
  with calculation_budget(10000,max_seconds=2):prepared=prepare_evaluation(g,b,roles.rules,strategy,max_work=10000,max_seconds=2)
  original=GeneralReuseForecast.full_renamed_key
  def intercept(e,*args,**kwargs):
   began=time.perf_counter();current=original(e,*args,**kwargs)
   current_seconds=time.perf_counter()-began
   captured.append((e,args,kwargs,current,current_seconds));raise FirstKeyReached()
  stopped=False
  with patch.object(GeneralReuseForecast,'full_renamed_key',intercept):
   try:
    response=c.get('/main');http=response.status_code
   except FirstKeyReached:stopped=True;http='diagnostic stop at first ordinary key'
  row=dict(role=role,start_http=303,publish_http=None if role=='plain'else 200,prepared_kind=prepared[0],exchangeable=InformationSetForecast(roles.rules,strategy).exchangeable(b),normal_http_key_reached=stopped,http=http,worlds=len(b.worlds),nontrivial_future_not_run=True)
  if captured:
   e,args,kwargs,current,current_seconds=captured[0];bb,s,past,private,observer=args;row['engine']=type(e).__name__;row['current_key_none']=current is None;row['current_decline_seconds']=current_seconds;row['hypotheses']=len(s.hypotheses)
   trials=[];expected=None
   for repeat in range(3):
    for kind in('full-enumeration','original-uncapped-pruned','planned'):
     started=time.perf_counter();plan=None
     with calculation_budget(10000,max_seconds=2):
      if kind=='planned':
       plan=KeyReusePlan();key=planned_key(bb,s,past,private,observer,e.rules,e.strategy,plan=plan,max_mappings=120,**kwargs)
      else:key=canonical_key(bb,s,past,private,observer,e.rules,e.strategy,max_mappings=1000,prune_automorphisms=kind!='full-enumeration',**kwargs)
     if expected is None:expected=key
     assert key is not None and key==expected
     trials.append(dict(kind=kind,repeat=repeat,seconds=time.perf_counter()-started,equal_complete_key=True,plan=None if plan is None else plan.summary()))
   row['trials']=trials
   if role=='medium':
    from werewolf.medium_value_key import public_descriptor,private_value_key
    descriptor=public_descriptor(bb,s,e.rules,e.strategy)
    row['existing_reduced_key']=None if descriptor is None else descriptor[0][0]
    row['existing_private_reduced_key']=private_value_key(descriptor,private)is not None if descriptor is not None else False
  rows.append(row)
 Path('benchmarks/player_match_groups/bounded-plan-reachability.json').write_text(json.dumps(dict(scope='normal UI setup and first-key interception; no nontrivial Forecast evaluated',results=rows),indent=2)+'\n')
 print(json.dumps(rows),flush=True)
if __name__=='__main__':run()