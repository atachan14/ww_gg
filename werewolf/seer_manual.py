"""Manual public seer evidence; no forecast acquisition/private use/disclosure.

Ordinary Board/Progress/solver semantics are retained. No real role selected.
Options are explicit and unresolved defaults never manufacture a win value.
"""
import json
from fractions import Fraction as F
from functools import lru_cache
from .exact import (initial_board,Progress,Rules,Strategy,ClaimPolicy,condition_claims,
    group_initial_board,replace_worlds,advance,validate_strategy,MediumReport,condition_reports,available_medium_opportunities)
from dataclasses import dataclass

@dataclass(frozen=True)
class ManualPending:
    reason: str

Pending = ManualPending

MODE='information-fixed-v1'
INITIAL=(None,'normal','random_white','none')
LIKELIHOOD=(None,'compatibility')

def migrate_game(game):
    """Approved deterministic migration; no changes to non-seer games."""
    if game.get('seer_mode') not in (None,'',MODE):raise ValueError('保存された占いモデルが未対応です。')
    if game.get('seer_mode')!=MODE and not game.get('seers',0):return game
    from copy import deepcopy
    g=deepcopy(game)
    old=g.get('seer_options',{})
    selected=g.get('rules',{}).get('initial_seer',old.get('initial_rule') or 'random_white')
    if selected not in ('normal','random_white','none') or old.get('likelihood') not in (None,'compatibility'):raise ValueError('保存された占いルールを確認してください。')
    if 'initial_seer' in g['rules'] and old.get('initial_rule') not in (None,selected):raise ValueError('Gameルールと保存された初日占いが一致しません。')
    g['rules']={**g['rules'],'initial_seer':selected}
    g['seer_mode']=MODE;g['seer_options']={'initial_rule':selected,'likelihood':'compatibility'}
    g.setdefault('seer_inputs',[])
    for step in g.get('history',[]):
        previous=step.get('seer_options',{})
        if previous.get('initial_rule') not in (None,selected) or previous.get('likelihood') not in (None,'compatibility'):raise ValueError('過去の初日占いスナップショットが一致しません。')
        step['seer_options']=dict(g['seer_options'])
        step.setdefault('claims',['latent']*g['players'])
        step.setdefault('claim_policy',{})
    return g


def options(value):
    if not isinstance(value,dict) or set(value)!={'initial_rule','likelihood'} or value['initial_rule'] not in INITIAL or value['likelihood'] not in LIKELIHOOD:
        raise ValueError('占いの初日ルール・報告尤度の設定を確認してください。')
    return dict(value)

def cast_scope(g):
    counts=tuple(g.get(k,0) for k in ('players','wolves','seers','mediums','hunters'))
    if any(type(x)is not int for x in counts):return False
    p,w,s,m,h=counts
    return 1<=p<=9 and all(x>=0 for x in (w,s,m,h)) and w+s+m+h<=p and w<=p

def input_rows(g):
    data=g.get('seer_inputs',[])
    if type(data) is not list:raise ValueError('占い入力台帳を確認してください。')
    seen=set()
    for row in data:
        if type(row) is not dict or set(row)!={'day','reporter','target','color'} or type(row['day']) is not int or row['day']<1 or type(row['reporter']) is not int or row['reporter'] not in range(1,g['players']+1):raise ValueError('占い結果の形式を確認してください。')
        if row['target'] is not None and (type(row['target']) is not int or row['target'] not in range(1,g['players']+1) or row['target']==row['reporter']):raise ValueError('自己占いは指定できません。対象を確認してください。')
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
            if row['day']==1 and opt['initial_rule']=='none':factor=F();break
            if row['day']==1 and opt['initial_rule']=='random_white':
                if row['color']!='white':factor=F();break
                legal=tuple(i for i in initial_alive if i!=row['reporter'] and not w&(1<<(i-1)))
                if row['target'] not in legal:factor=F();break
                factor/=len(legal)
        if factor:entries.append((w,m,s,h,q*factor))
    mass=sum((x[-1] for x in entries),F())
    if not mass:raise ValueError('占い結果と公開履歴に整合する配役がありません。')
    return replace_worlds(board,tuple((*x[:-1],x[-1]/mass) for x in entries))

def replay(game):return _replay(json.dumps(migrate_game(game),sort_keys=True,separators=(',',':'),allow_nan=False))

@lru_cache(maxsize=32)
def _replay(text):
    g=json.loads(text)
    if g.get('seer_mode')!=MODE or not cast_scope(g):raise ValueError('手動開発版は1～9人・非負の役職数・合計人数の範囲で指定してください。')
    opt=options(g.get('seer_options',{}));rows=input_rows(g)
    rules=Rules(**g['rules']);seed=initial_board(g['players'],g.get('wolves',1),g.get('mediums',0),g.get('seers',0),g.get('hunters',0),experimental_cast=True);p=Progress.initial(seed);initial=seed.alive
    medium_rows=tuple(MediumReport(**r) for r in g.get('reports',()))
    medium_applied=set()
    from .report_publication import publication_slot,condition_published_medium
    history=g['history']
    if type(history) is not list or len(history)>max(0,g['players']-2):raise ValueError('保存された進行を確認してください。')
    if history and history[0].get('seer_options')!=opt:raise ValueError('初日ルール・報告尤度の変更は初日へ戻って行ってください。')
    applied=set();scan={1:initial}
    def apply(p,claims,cp,group=False):
        if p.finished:return p
        board=group_initial_board(p.board,claims,cp) if group else condition_claims(p.board,claims,cp)
        slot=2*(board.day-1)+(board.phase=='night')
        selected_medium=tuple(r for r in medium_rows if publication_slot(g,'medium',{'day':r.day,'reporter':r.reporter,'target':r.target})<=slot and (r.day,r.reporter,r.target) not in medium_applied)
        if selected_medium:
            board=condition_published_medium(board,selected_medium,history)
            medium_applied.update((r.day,r.reporter,r.target) for r in selected_medium)
        if board.phase=='night':scan[board.day+1]=board.alive
        selected=tuple(r for r in rows if publication_slot(g,'seer',r)<=slot and (r['day'],r['reporter']) not in applied)
        for row in selected:
            if row['reporter'] not in board.alive or claims[row['reporter']-1]!='seer':raise ValueError('結果の公開時点に生存・占いCOしている報告者を指定してください。')
            if row['target'] is not None and row['target'] not in scan[row['day']]:raise ValueError('取得時点に生存していた対象を指定してください。')
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
    if any((r.day,r.reporter,r.target) not in medium_applied for r in medium_rows):raise ValueError('霊能報告と保存された公開機会が一致しません。')
    validate_strategy(rules,Strategy(**g['policy']))
    return rules,p

def pending(g):
    g=migrate_game(g)
    opt=options(g['seer_options'])
    if opt['initial_rule'] is None:return Pending('Boardの「戦略」を開き、「初日ルール」を選択してください。')
    if opt['likelihood'] is None:return Pending('Boardの「戦略」を開き、「入力報告の扱い」を選択してください。選択するまで勝率は未計算です。')
    if any((r['target'] is None)!=(r['color'] is None) for r in input_rows(g)):return Pending('占いの対象と白黒結果を揃えてください。')
    return None

def parse_form(form,g,board):
    result=dict(g);opt=dict(g['seer_options'])
    for field in ('initial_rule','likelihood'):
        key='seer_'+field;values=form.getlist(key)
        if values:
            if len(values)!=1:raise ValueError('占い設定が重複しています。')
            chosen=values[0] or None
            if chosen != opt[field]:raise ValueError('初日占いはTOPのGameルールで設定してください。入力報告の扱いは固定です。')
    options(opt)
    if g['history'] and opt!=g['seer_options']:raise ValueError('初日ルール・尤度を変える場合は初日へ戻ってください。')
    rows={(r['day'],r['reporter']):dict(r) for r in g['seer_inputs']}
    for day in range(1,board.day+1):
        for player in range(1,g['players']+1):
            a,b=f'seer_target_{day}_{player}',f'seer_color_{day}_{player}'
            av,bv=form.getlist(a),form.getlist(b)
            if not av and not bv:continue
            if len(av)!=1 or len(bv)!=1 or av[0] not in ('',*(str(i) for i in range(1,g['players']+1))) or bv[0] not in ('','white','black'):raise ValueError('占い対象・色の入力を確認してください。')
            if not av[0] and not bv[0]:rows.pop((day,player),None)
            else:rows[day,player]={'day':day,'reporter':player,'target':int(av[0]) if av[0] else None,'color':bv[0] or None}
    result.update(seer_options=opt,seer_inputs=[rows[k] for k in sorted(rows)])
    input_rows(result)
    return result

def trim_back(g):
    max_day=1+len(g['history'])//2
    return {**g,'seer_inputs':[r for r in g['seer_inputs'] if r['day']<=max_day],**({'reports':[r for r in g['reports'] if r['day']<=max_day]} if 'reports' in g else {})}

def timeline(g,board,player,finished=False):
    data={(r['day'],r['reporter']):r for r in g['seer_inputs']};rows=[]
    for day in range(1,board.day+1):
        alive=set(range(1,g['players']+1));scan=set(alive)
        for event in board.history:
            if event.day<day:alive.discard(event.target)
            if day>1 and (event.day<day-1 or event.day==day-1 and event.phase=='day'):scan.discard(event.target)
        claim_index=2*(day-1)
        claims=g['history'][claim_index]['claims'] if claim_index<len(g['history']) else g['claims']
        if player not in alive or (claims[player-1]!='seer' and not (g.get('public_log',{}).get('version')==2 and (g['claims'][player-1]=='seer' or (day,player) in data))):continue
        row=data.get((day,player),{'target':None,'color':None})
        rows.append({'day':day,'target':row['target'],'color':row['color'],'targets':tuple(i for i in sorted(scan) if i!=player),'editable':not finished,'initial_none':day==1 and g['seer_options']['initial_rule']=='none' and row['target'] is None and row['color'] is None})
    return rows
