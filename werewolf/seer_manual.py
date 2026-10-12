"""Manual public seer evidence; no forecast acquisition/private use/disclosure.

Ordinary Board/Progress/solver semantics are retained. No real role selected.
Options are explicit and unresolved defaults never manufacture a win value.
"""
import json
from fractions import Fraction as F
from functools import lru_cache
from .exact import (initial_board,Progress,Rules,Strategy,ClaimPolicy,condition_claims,
    group_initial_board,replace_worlds,advance,validate_strategy)
from dataclasses import dataclass

@dataclass(frozen=True)
class ManualPending:
    reason: str

Pending = ManualPending

MODE='information-fixed-v1'
INITIAL=(None,'normal','random_white','none')
LIKELIHOOD=(None,'compatibility')

def options(value):
    if not isinstance(value,dict) or set(value)!={'initial_rule','likelihood'} or value['initial_rule'] not in INITIAL or value['likelihood'] not in LIKELIHOOD:
        raise ValueError('占いの初日ルール・報告尤度の設定を確認してください。')
    return dict(value)

def cast_scope(g):
    return all(type(g.get(k,0)) is int for k in ('players','wolves','seers','mediums','hunters')) and (g.get('players'),g.get('wolves'),g.get('seers'),g.get('mediums',0),g.get('hunters',0))==(5,2,1,0,0)

def input_rows(g):
    data=g.get('seer_inputs',[])
    if type(data) is not list:raise ValueError('占い入力台帳を確認してください。')
    seen=set()
    for row in data:
        if type(row) is not dict or set(row)!={'day','reporter','target','color'} or type(row['day']) is not int or row['day']<1 or type(row['reporter']) is not int or row['reporter'] not in range(1,6):raise ValueError('占い結果の形式を確認してください。')
        if row['target'] is not None and (type(row['target']) is not int or row['target'] not in range(1,6) or row['target']==row['reporter']):raise ValueError('自己占いは指定できません。対象を確認してください。')
        if row['color'] not in (None,'white','black'):raise ValueError('占い結果は白・黒を選択してください。')
        key=(row['day'],row['reporter'])
        if key in seen:raise ValueError('同じ日の結果が重複しています。')
        seen.add(key)
    return tuple(sorted(data,key=lambda r:(r['day'],r['reporter'])))

def condition(board,rows,opt,initial_alive):
    if not rows:return board
    entries=[]
    for w,m,s,h,q in board.worlds:
        factor=F(1)
        for row in rows:
            if not s&(1<<(row['reporter']-1)):continue # Fake report is not truth.
            if (row['color']=='black') != bool(w&(1<<(row['target']-1))):factor=F();break
            if row['day']==1 and opt['initial_rule']=='random_white':
                if row['color']!='white':factor=F();break
                legal=tuple(i for i in initial_alive if i!=row['reporter'] and not w&(1<<(i-1)))
                if row['target'] not in legal:factor=F();break
                factor/=len(legal)
        if factor:entries.append((w,m,s,h,q*factor))
    mass=sum((x[-1] for x in entries),F())
    if not mass:raise ValueError('占い結果と公開履歴に整合する配役がありません。')
    return replace_worlds(board,tuple((*x[:-1],x[-1]/mass) for x in entries))

def replay(game):return _replay(json.dumps(game,sort_keys=True,separators=(',',':'),allow_nan=False))

@lru_cache(maxsize=32)
def _replay(text):
    g=json.loads(text)
    if g.get('seer_mode')!=MODE or not cast_scope(g):raise ValueError('手動占いは5人・占い1・市民2・狼2（霊能/狩人なし）に限定しています。')
    opt=options(g.get('seer_options',{}));rows=input_rows(g)
    rules=Rules(**g['rules']);p=Progress.initial(initial_board(5,2,0,1,0));initial=p.board.alive
    history=g['history']
    if type(history) is not list or len(history)>3:raise ValueError('保存された進行を確認してください。')
    if history and history[0].get('seer_options')!=opt:raise ValueError('初日ルール・報告尤度の変更は初日へ戻って行ってください。')
    applied=set();contexts={};scan={1:initial}
    def apply(p,claims,cp,group=False):
        if p.finished:return p
        board=group_initial_board(p.board,claims,cp) if group else condition_claims(p.board,claims,cp)
        if board.phase=='night':scan[board.day+1]=board.alive
        if board.phase=='day':
            contexts.setdefault(board.day,(board.alive,claims))
            selected=tuple(r for r in rows if r['day']==board.day and (r['day'],r['reporter']) not in applied)
            for row in selected:
                if row['reporter'] not in board.alive or claims[row['reporter']-1]!='seer':raise ValueError('結果の公開時点に生存・占いCOしている報告者を指定してください。')
                if row['target'] is not None and row['target'] not in scan[board.day]:raise ValueError('取得時点に生存していた対象を指定してください。')
                if row['day']==1 and opt['initial_rule']=='none' and (row['target'] is not None or row['color'] is not None):raise ValueError('初日なしでは初日結果を入力できません。')
            complete=tuple(r for r in selected if r['target'] is not None and r['color'] is not None)
            if opt['initial_rule'] is not None and opt['likelihood'] is not None:board=condition(board,complete,opt,initial)
            applied.update((r['day'],r['reporter']) for r in selected)
        return Progress(board,p.settled_village,p.settled_wolf,p.last_board,p.last_outcomes)
    for i,step in enumerate(history):
        if p.finished:raise ValueError('入力結果と保存済みの進行が不整合です。戻って確認してください。')
        allowed={'target','policy','claims','claim_policy','strategy_ui','reports','seer_options'}
        if not isinstance(step,dict) or set(step)-allowed or not {'target','policy','claims','claim_policy','seer_options'}<=set(step):raise ValueError('手動占いの保存履歴を確認してください。')
        p=apply(p,tuple(step['claims']),ClaimPolicy(**step['claim_policy']),i==0 and g.get('model','equal')=='group')
        p=advance(p,step['target'],rules,Strategy(**step['policy']))
    if not p.finished:p=apply(p,tuple(g['claims']),ClaimPolicy(**g['claim_policy']),not history and g.get('model','equal')=='group')
    if any((r['day'],r['reporter']) not in applied for r in rows):raise ValueError('まだ到達していない日の結果は入力できません。')
    validate_strategy(rules,Strategy(**g['policy']))
    return rules,p

def pending(g):
    opt=options(g['seer_options'])
    if opt['initial_rule'] is None or opt['likelihood'] is None:return Pending('初日ルールと報告尤度を選択してください。')
    root=g['history'][0] if g['history'] else g
    claims=root['claims']
    if claims.count('seer')!=2 or any(x not in ('seer','latent') for x in claims):return Pending('この版は初日の占いCO2・潜伏3に限定しています。')
    if not ClaimPolicy(**root['claim_policy']).conditions('seer'):return Pending('この版は真占いのCO必須条件を使います。')
    if any((r['target'] is None)!=(r['color'] is None) for r in input_rows(g)):return Pending('占いの対象と白黒結果を揃えてください。')
    return None

def parse_form(form,g,board):
    result=dict(g);opt=dict(g['seer_options'])
    for field in ('initial_rule','likelihood'):
        key='seer_'+field;values=form.getlist(key)
        if values:
            if len(values)!=1:raise ValueError('占い設定が重複しています。')
            opt[field]=values[0] or None
    options(opt)
    if g['history'] and opt!=g['seer_options']:raise ValueError('初日ルール・尤度を変える場合は初日へ戻ってください。')
    rows={(r['day'],r['reporter']):dict(r) for r in g['seer_inputs']}
    for day in range(1,board.day+1):
        for player in range(1,6):
            a,b=f'seer_target_{day}_{player}',f'seer_color_{day}_{player}'
            av,bv=form.getlist(a),form.getlist(b)
            if not av and not bv:continue
            if len(av)!=1 or len(bv)!=1 or av[0] not in ('','1','2','3','4','5') or bv[0] not in ('','white','black'):raise ValueError('占い対象・色の入力を確認してください。')
            if not av[0] and not bv[0]:rows.pop((day,player),None)
            else:rows[day,player]={'day':day,'reporter':player,'target':int(av[0]) if av[0] else None,'color':bv[0] or None}
    result.update(seer_options=opt,seer_inputs=[rows[k] for k in sorted(rows)])
    input_rows(result)
    return result

def trim_back(g):
    max_day=1+len(g['history'])//2
    return {**g,'seer_inputs':[r for r in g['seer_inputs'] if r['day']<=max_day]}

def timeline(g,board,player,finished=False):
    data={(r['day'],r['reporter']):r for r in g['seer_inputs']};rows=[]
    for day in range(1,board.day+1):
        alive=set(range(1,6));scan=set(alive)
        for event in board.history:
            if event.day<day:alive.discard(event.target)
            if day>1 and (event.day<day-1 or event.day==day-1 and event.phase=='day'):scan.discard(event.target)
        if player not in alive:continue
        row=data.get((day,player),{'target':None,'color':None})
        rows.append({'day':day,'target':row['target'],'color':row['color'],'targets':tuple(i for i in sorted(scan) if i!=player),'editable':not finished,'initial_none':day==1 and g['seer_options']['initial_rule']=='none'})
    return rows
