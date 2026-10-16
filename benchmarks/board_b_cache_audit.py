"""Cache mutation audit: warmed mixed requests must equal fresh-process results."""
import argparse,copy,importlib,importlib.util,json,pkgutil,subprocess,sys
from pathlib import Path
from board_b_benchmark import ROOT,BUDGET,canonical,digest,census_pending


def request(case,new,oracle):
    from werewolf.exact import Strategy,ROLES,legal_targets
    before=digest(case);game=copy.deepcopy(case['game']);game_before=digest(game);strategy=Strategy(**game['policy'])
    if new:
        from werewolf.board_flow import BoardData
        state=BoardData.from_game(game).roles();rules,progress=state.replay_result
    else:
        from werewolf.seer_manual import replay
        rules,progress=replay(game) if game.get('seer_mode')=='information-fixed-v1' else oracle.reconstruct_saved(game)
    board=progress.last_board if progress.finished else progress.board
    if case['view']=='public':
        if new:result=state.forecast(**BUDGET)
        else:
            from werewolf.model_a_public import evaluate_public_game
            result=evaluate_public_game(game,board,rules,strategy,**BUDGET)
    else:
        v=case['private']
        if new:result=state.private(v['role'],v['players'],v['results'],**BUDGET)
        else:
            from werewolf.private_adapter import evaluate_private_table
            result=evaluate_private_table(board,v['role'],v['players'],v['results'],rules,strategy,game_state=game,**BUDGET)
    pending=census_pending(result)
    if case['view']=='private' and any(r['legal'] and r['final'] is None for r in result.get('players',())):pending.append(result['reason'])
    value=canonical({'worlds':tuple(sorted(board.worlds)),'roles':tuple({r:board.role_probability(p,r) for r in ROLES} for p in range(1,board.player_count+1)),
       'legal':legal_targets(board,rules,strategy),'progress':progress,'result':result,'pending':pending})
    assert before==digest(case),'View/case input mutated'
    assert game_before==digest(game),'Passed game input mutated'
    return {'semantic':value,'digest':digest(value),'pending':pending,'input_digest':before}


def worker(a):
    sys.path.insert(0,a.tree)
    import werewolf
    for m in pkgutil.iter_modules(werewolf.__path__):importlib.import_module('werewolf.'+m.name)
    spec=importlib.util.spec_from_file_location('audit_oracle',ROOT/'tests/fixtures/board_replay_v051.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    cases=json.loads(Path(a.cases).read_text(encoding='utf-8'))
    rows=[dict(case=name,**request(cases[name],a.version=='new',oracle)) for name in a.sequence.split(',')]
    Path(a.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')


def run(a):
    output=Path(a.output).resolve();output.mkdir(parents=True,exist_ok=True)
    cases=json.loads(Path(a.cases).read_text(encoding='utf-8'));all_versions={};failures=[]
    for version in ('old','new'):
        def invoke(sequence,label):
            target=output/(version+'-'+label+'.json')
            subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'worker','--tree',str(Path(a.snapshots).resolve()/version),'--cases',str(Path(a.cases).resolve()),'--version',version,'--sequence',','.join(sequence),'--output',str(target)],check=True,timeout=180)
            return json.loads(target.read_text(encoding='utf-8'))
        sequence=['base']
        for name in cases:
            if name!='base':sequence.extend([name,'base'])
        warm=invoke(sequence,'mixed-warm');fresh={name:invoke([name],'fresh-'+name)[0] for name in cases}
        for row in warm:
            if row['digest']!=fresh[row['case']]['digest']:failures.append([version,row['case'],'warm-fresh'])
        all_versions[version]={'warm':warm,'fresh':fresh}
    for name in cases:
        if all_versions['old']['fresh'][name]['digest']!=all_versions['new']['fresh'][name]['digest']:failures.append([name,'old-new'])
    result={'cases_file_digest':digest(cases),'cases':list(cases),'input_immutability_checked':True,'warm_request_count_per_version':len(sequence),'versions':all_versions,'failures':failures,'note':'Cache equality is not a proof of old mathematical correctness; unsupported/partial rows remain uncomputed.'}
    (output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(cases),'warm_per_version':len(sequence),'failures':failures},ensure_ascii=False),flush=True)
    if failures:raise AssertionError(failures)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('run');q.add_argument('--snapshots',required=True);q.add_argument('--output',required=True);q.add_argument('--cases',default=str(ROOT/'benchmarks/board_b_cache_cases.json'))
    q=s.add_parser('worker');q.add_argument('--tree',required=True);q.add_argument('--cases',required=True);q.add_argument('--version',required=True);q.add_argument('--sequence',required=True);q.add_argument('--output',required=True)
    a=p.parse_args();run(a) if a.command=='run' else worker(a)
if __name__=='__main__':main()
