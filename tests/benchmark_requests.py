"""Local-only cold-cache HTTP request benchmark; no public benchmark endpoint.

Run from repo: python tests/benchmark_requests.py --output docs/vercel-request-benchmark.json
Each GET evaluates the complete remaining exact game, including every target.
Each case then advances a continuing manual history to a terminal Board.
"""
import argparse
import json
import sys
import time
import tracemalloc
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from werewolf.exact import (solve, symmetric_action, Progress, Rules, Strategy, ClaimPolicy,
    initial_board, group_initial_board, condition_claims, advance, action_outcomes)
from werewolf.reports import solve_reports, disclosure

def clear():
    for function in (solve, symmetric_action, solve_reports, disclosure):
        function.cache_clear()

def replay(state):
    rules = Rules(**state['rules'])
    p = Progress(initial_board(state['players'], state['wolves'], state['mediums'], state.get('seers',0), state.get('hunters',0)))
    for index, step in enumerate(state['history']):
        b = group_initial_board(p.board, tuple(step['claims']), ClaimPolicy(**step['claim_policy'])) if index==0 else condition_claims(p.board, tuple(step['claims']), ClaimPolicy(**step['claim_policy']))
        p = advance(Progress(b,p.settled_village,p.settled_wolf),step['target'],rules,Strategy(**step['policy']))
    if not p.finished:
        b = group_initial_board(p.board, tuple(state['claims']), ClaimPolicy(**state['claim_policy'])) if not state['history'] else condition_claims(p.board,tuple(state['claims']),ClaimPolicy(**state['claim_policy']))
        p = Progress(b,p.settled_village,p.settled_wolf)
    return p

def run_case(n, wolves=1, mediums=0, seers=0, hunters=0, claims=()):
    app = create_app({'TESTING':True, 'SECRET_KEY':'benchmark-public-fixture'})
    client = app.test_client()
    records = []
    def request(method, path, data=None):
        clear()
        tracemalloc.start()
        started = time.perf_counter()
        response = client.open(path, method=method, data=data)
        elapsed = time.perf_counter()-started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        header = response.headers.get('Set-Cookie','')
        records.append({'method':method,'path':path,'status':response.status_code,'seconds':elapsed,
                        'python_peak_bytes':peak,'response_bytes':len(response.data),
                        'set_cookie_bytes':len(header.encode('ascii'))})
        if response.status_code not in (200,303):
            raise RuntimeError(f'{method} {path}: {response.status_code}')
        return response
    request('POST','/start',{'citizens':str(n-wolves-mediums-seers-hunters),'wolves':str(wolves),
        'mediums':str(mediums),'seers':str(seers),'hunters':str(hunters),'day':'max','night':'max',
        **{'cco_'+r:'none' for r in ('villager','medium','seer','hunter')}})
    if claims:
        request('POST','/strategy',{'revision':'0','day':'max','night':'max',
                **{'co_'+str(i+1):claim for i,claim in enumerate(claims)}})
    phases = 0
    while True:
        with client.session_transaction() as session:
            state = dict(session['game'])
        p = replay(state)
        if p.finished:
            request('GET','/result')
            break
        request('GET','/main')
        phases += 1
        rules, strategy = Rules(**state['rules']), Strategy(**state['policy'])
        from werewolf.exact import legal_targets
        candidates = legal_targets(p.board,rules,strategy)
        target = next((i for i in candidates if any(o.board.winner is None for o in action_outcomes(p.board,i,rules,strategy))),candidates[0])
        request('POST','/advance',{'revision':str(state['revision']),'day':'max','night':'max','target':str(target)})
    return {'players':n,'wolves':wolves,'mediums':mediums,'seers':seers,'hunters':hunters,
            'claims':claims,'phases':phases,'requests':records,
            'max_request_seconds':max(r['seconds'] for r in records),
            'max_python_peak_bytes':max(r['python_peak_bytes'] for r in records),
            'max_set_cookie_bytes':max(r['set_cookie_bytes'] for r in records)}

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    cases=[]
    for n in range(3,10):
        result=run_case(n,1 if n<5 else 2)
        cases.append(result)
        print(json.dumps({k:result[k] for k in ('players','phases','max_request_seconds','max_set_cookie_bytes')}),flush=True)
    result=run_case(9,2,2,1,1,('medium','medium')+('latent',)*7)
    cases.append(result)
    print(json.dumps({k:result[k] for k in ('players','phases','max_request_seconds','max_set_cookie_bytes')}),flush=True)
    Path(args.output).write_text(json.dumps({'method':'Flask test client; each HTTP request separately timed with cold engine caches and tracemalloc; full manual history to terminal; no network/cloud capacity claim','cases':cases},indent=2),encoding='utf-8')
