"""Local TreeItems over real Closed nodes; exact established renaming groups.

The display quotient keeps every named member and its actual probability.
Complete Q/P/history/physical signatures, not equal values, define groups.
"""
from dataclasses import asdict
from fractions import Fraction as F
from hashlib import sha256
from threading import RLock
from .closed_calculation import ClosedCalculation
from .exact import Strategy,legal_targets
from .evaluation_branch import physical_board
from .exact_renaming import canonical_key
from .calculation_budget import tick


def supported(data,board):
    g=data.game_data
    return (g.players==5 and g.wolves==1 and g.seers==1 and not(g.mediums or g.hunters)
            and not g.rules.allow_self_bite)


def explain_unavailable(game,reason):
    """Describe actual saved inputs without changing them or weakening admission."""
    counts={role:game.get(role,0) for role in ('wolves','seers','mediums','hunters')}
    counts['wolves']=game.get('wolves',1)
    counts['citizens']=game['players']-sum(counts.values())
    strategy=Strategy(**game['policy']);rules=game['rules'];issues=[]
    if counts!=dict(citizens=3,seers=1,wolves=1,mediums=0,hunters=0):
        issues.append('配役が対応範囲（市民3・占い1・狼1、霊能0・狩人0）と異なります。')
    if rules.get('allow_self_bite'):issues.append('自噛み可能のルールは未対応です。')
    if rules.get('initial_seer','random_white')!='random_white':issues.append('初日占いはランダム白のみ対応しています。')
    if (strategy.day,strategy.night,strategy.fake_reports) not in (('max',)*3,('random',)*3):
        issues.append('昼・夜・狼の霊能騙り報告の方針が混在しています。現経路は3項目すべてMAX、またはすべてランダムのみ対応しています。')
    if any(strategy.disclosure_for(role)!='all' for role in ('seer','medium')):
        issues.append('能力結果の公開方針は全公開のみ対応しています。')
    if not issues:
        messages={
            'game_tree_finished':'現在の保存Boardは終局しています。',
            'closed_saved_public_or_policy_change_pending':'過去BoardからCO・方針・公開条件が変化した履歴、または必要な公開履歴が未確定のBoardは、このGameTree経路で未対応です。',
            'closed_saved_nonstandard_observation_pending':'特殊な死亡・観測を含む保存履歴は、このGameTree経路で未対応です。',
            'closed_saved_late_public_event_pending':'途中の公開イベントを含む保存履歴は、このGameTree経路で未対応です。',
            'forecast_pending':'現在のBoardの継続評価が未確定です。'}
        issues.append(messages.get(reason,'現在の保存条件は既存の共通継続評価の対応範囲外です。'))
    return dict(error='現在の入力ではGameTreeを表示できません。',reason=reason,issues=issues,
        actual=dict(counts=counts,policy=dict(day=strategy.day,night=strategy.night,fake_reports=strategy.fake_reports),rules=rules,history_steps=len(game.get('history',[]))),
        supported_route='新しく試す場合はTOPで市民3・占い1・狼1（霊能0・狩人0）、自噛み不可、初日占いランダム白を指定してください。既定の昼夜MAX・全公開で初日から表示できます。',
        settings_url='/',preserved=True)


class CalculationTree:
    def __init__(self,data,board,forecast):
        if not supported(data,board):raise ValueError('Five-player3citizen/1seer/1wolf scope')
        self.data=data;self.rules=data.game_data.rules;self.strategy=Strategy(**data.to_game()['policy'])
        self.calculation=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
        self.engine=self.calculation._ClosedCalculation__engine
        self.snapshot=sha256(data.inputs.encode()).hexdigest()[:20]
        self.nodes={};self.sources={};self.keys={};self.values={};self.lock=RLock()
        self.root=self.register(self.calculation.root)
        # Root value is the actual BoardOverview result, never a fixture value.
        self.nodes[self.root]['value']=forecast.village_win

    def equivalence(self,node,target=None):
        s=node.read();key=(s,target)
        if key not in self.keys:
            self.keys[key]=canonical_key(*s,self.rules,self.strategy,target=target,physical=s.physical,max_mappings=120)
        return self.keys[key] or ('unshared',key)

    def register(self,node):
        s=node.read()
        if s in self.sources:return self.sources[s]
        key=str(len(self.nodes));self.sources[s]=key
        self.nodes[key]={'node':node,'value':None,'actions':None,'reused':False}
        return key

    def value(self,key):
        row=self.nodes[key]
        if row['value'] is not None:return row['value']
        node=row['node'];s=node.read();canonical=self.equivalence(node)
        if canonical in self.values:row['value']=self.values[canonical];row['reused']=True
        else:
            with self.calculation._ClosedCalculation__kernel(),self.engine.group_scope(node.groups):
                from .closed_calculation import _forecast_scope
                _forecast_scope(s,self.engine)
                row['value']=self.engine.solve(*s,physical=s.physical)
            self.values[canonical]=row['value']
        return row['value']

    def candidates(self,node):
        e=self.engine;s=node.read();b=s.public
        if b.winner:return []
        rows=[]
        with self.calculation._ClosedCalculation__kernel(),e.group_scope(node.groups):
            if b.phase=='day':
                scores=dict(e.day_scores(b,s.public_state,s.past))
                best=max(scores.values());selected=[t for t,v in scores.items() if e.strategy.day=='random' or v==best]
                for target in legal_targets(s.physical,self.rules,self.strategy):
                    rows.append({'node':node,'target':target,'q_score':scores[target],
                        'policy_mass':F(1,len(selected)) if target in selected else F(),
                        'fallback_mass':F(1,len(scores)),'information':'公開Q'})
            else:
                # Selection is from PUBLIC Q conditioned by actor information;
                # actual weights and child Boards come from the existing P split.
                choices=node.wolf_choices();owners={}
                for choice in choices:owners.setdefault(choice.information,(choice.node,choice.information_mass,{}))[2][choice.target]=choice.probability
                for info,(owned,mass,policy) in owners.items():
                    own=owned.read();q_actor=info.condition_public(s.public_state)
                    with e.actor_scope(info):
                        for target in legal_targets(own.physical,self.rules,self.strategy):
                            score=e.act(b,s.public_state,s.past,target,q_actor,None,physical=physical_board(b,q_actor))
                            rows.append({'node':owned,'target':target,'q_score':score,
                                'policy_mass':mass*policy.get(target,F()),'fallback_mass':mass/F(len(legal_targets(own.physical,self.rules,self.strategy))),
                                'information':f'狼本人I (初期狼集合{info.initial_roster})'})
        return rows

    def expand(self,key):
        record=self.nodes[key]
        if record['actions'] is not None:return
        node=record['node'];groups={}
        for row in self.candidates(node):groups.setdefault(self.equivalence(row['node'],row['target']),[]).append(row)
        choices=[]
        for members in groups.values():
            policy_mass=sum((r['policy_mass'] for r in members),F())
            normalizer=policy_mass or sum((r['fallback_mass'] for r in members),F())
            branches={};named=[]
            for member in members:
                tick();origin=member['node'];s=origin.read();target=member['target']
                weight=(member['policy_mass'] if policy_mass else member['fallback_mass'])/normalizer
                named.append({'target':target,'information':member['information'],'policy_mass':str(member['policy_mass'])})
                if not weight:continue
                for physical in origin.action(target):
                    after=physical.node
                    reports=after.reports() if s.public.phase=='night' and after.read().public.winner is None else None
                    outcomes=[(r.probability,r.node) for r in reports] if reports else [(F(1),after)]
                    for report_mass,child in outcomes:
                        source=child.read();chance=physical.probability*report_mass
                        child_id=self.register(child);canonical=self.equivalence(child)
                        observation=('村勝利' if source.public.winner=='village' else '狼勝利' if source.public.winner=='wolf' else '継続')
                        new_reports=[r for r in source.past if r not in s.past]
                        if new_reports:observation+='・'+','.join(f'P{r.player}→P{r.target}{r.color}' for r in new_reports)
                        bucket=branches.setdefault(canonical,{'node':child_id,'probability':F(),'variants':[],'observation':observation})
                        bucket['probability']+=weight*chance
                        bucket['variants'].append({'node':child_id,'target':target,'information':member['information'],
                            'conditional_probability':str(chance),'mixture_probability':str(weight*chance)})
            target_ids=sorted({r['target'] for r in members})
            for branch in branches.values():branch['probability']=str(branch['probability'])
            choices.append({'targets':target_ids,'label':('処刑' if node.read().public.phase=='day' else '襲撃')+' '+ '/'.join('P'+str(p) for p in target_ids),
                'multiplicity':len(members),'members':named,'q_score':str(members[0]['q_score']),
                'selected':bool(policy_mass),'policy_probability':str(policy_mass),'branches':list(branches.values())})
        record['actions']=choices

    def summary(self,key,actions=False):
        row=self.nodes[key];node=row['node'];s=node.read();b=s.public;value=self.value(key)
        return {'snapshot':self.snapshot,'node':key,'day':b.day,'phase':b.phase,'alive':list(b.alive),'winner':b.winner,
            'viewpoint':'公開Qで方針決定 / 物理Pで評価'+('（本人条件付き枝）' if s.private!=s.public_state else ''),
            'village_win':str(value),'wolf_win':str(1-value),'evaluation':'computed',
            'expansion':'computed' if row['actions'] is not None or b.winner else 'pending','reused':row['reused'],
            'mode':getattr(self.strategy,b.phase),'rules':asdict(self.rules),'policy':asdict(self.strategy),
            'history':[asdict(e) for e in b.history],'reports':[asdict(r) for r in s.past],
            'players':[{'player':p,'alive':p in b.alive,'wolf_probability':str(b.wolf_probability(p)),
                'seer_probability':str(b.role_probability(p,'seer')),
                'physical_wolf_probability':str(sum((h.mass for h in s.private.hypotheses if h.roles[0]&(1<<(p-1))),F()))} for p in range(1,b.player_count+1)],
            'actions':row['actions'] if actions else None,'fixture':'市民3・占い1・狼1。CO・公開結果は保存入力どおり（追加なし）。',
            'method':'完全なQ/P・履歴・物理枝の既存の名前付替え同値でまとめます。全ての成員Boardを選択できます。'}

    def read(self,key,expand=False):
        with self.lock:
            if key not in self.nodes:raise KeyError(key)
            if expand:self.expand(key)
            result=self.summary(key,True);items={}
            for choice in result['actions'] or []:
                for branch in choice['branches']:items[branch['node']]=self.summary(branch['node'])
            result['items']=items;return result
