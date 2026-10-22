"""Local TreeItems over real Closed nodes; exact established renaming groups.

The display quotient keeps every named member and its actual probability.
Complete Q/P/history/physical signatures, not equal values, define groups.
"""
from dataclasses import asdict,replace
from fractions import Fraction as F
from hashlib import sha256
from threading import RLock
from .closed_calculation import ClosedCalculation
from .exact import Strategy,legal_targets
from .evaluation_branch import physical_board
from .exact_renaming import canonical_key
from .calculation_budget import tick


def input_snapshot(data):return sha256(data.inputs.encode()).hexdigest()[:20]

def supported(data,board):
    g=data.game_data
    return (g.wolves>=1 and g.hunters<=1
            and not g.rules.allow_self_bite)


def explain_unavailable(game,reason):
    """Describe actual saved inputs without changing them or weakening admission."""
    counts={role:game.get(role,0) for role in ('wolves','seers','mediums','hunters')}
    counts['wolves']=game.get('wolves',1)
    counts['citizens']=game['players']-sum(counts.values())
    strategy=Strategy(**game['policy']);rules=game['rules'];issues=[]
    if counts['hunters']>1:issues.append('複数狩人の護衛は未対応です。')
    if counts['hunters'] and (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3:issues.append('狩人を含む段階GameTreeは全ランダム方策のみ対応しています。MAX方策は未対応です。')
    if rules.get('allow_self_bite'):issues.append('自噛み可能のルールは未対応です。')
    if counts['seers'] and rules.get('initial_seer','random_white')!='random_white':issues.append('初日占いはランダム白のみ対応しています。')
    if (strategy.day,strategy.night,strategy.fake_reports) not in (('max',)*3,('random',)*3):
        issues.append('昼・夜・人狼の霊能騙り報告の方針が混在しています。現経路は3項目すべてMAX、またはすべてランダムのみ対応しています。')
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
        supported_route='段階GameTreeは自噛み不可・全公開の既存厳密範囲で利用できます。占い師がいる場合は初日ランダム白が必要です。霊能は既存報告規則、狩人は1人・全ランダム方策に対応します。',
        settings_url='/',preserved=True)


def composition_label(composition,game_data,role_order):
    from .exact import ROLE_LABELS
    w,m,seer,h,v=composition
    counts=dict(wolf=w,medium=m,seer=seer,hunter=h,villager=v)
    initial=dict(wolf=game_data.wolves,medium=game_data.mediums,seer=game_data.seers,hunter=game_data.hunters,
        villager=game_data.players-game_data.wolves-game_data.mediums-game_data.seers-game_data.hunters)
    return ''.join(('\u5360\u3044' if role=='seer' else ROLE_LABELS[role])+str(counts[role]) for role in role_order if initial[role])


class DeferredNode:
    def __init__(self,resolve):self.resolve=resolve;self.node=None
    def __getattr__(self,name):
        if self.node is None:self.node=self.resolve()
        return getattr(self.node,name)


class CalculationTree:
    def __init__(self,data,board,forecast,*,role_order=None,anonymous=False):
        if not supported(data,board):raise ValueError('Closed exact seer/wolf stage scope')
        from .exact import ROLES
        self.role_order=tuple(ROLES if role_order is None else role_order)
        self.data=data;self.rules=data.game_data.rules;self.strategy=Strategy(**data.to_game()['policy'])
        self.calculation=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=anonymous)
        self.engine=self.calculation._ClosedCalculation__engine
        self.snapshot=input_snapshot(data)
        self.nodes={};self.sources={};self.keys={};self.values={};self.traces={};self.lock=RLock()
        self.entry_node=self.calculation.root
        self.root=self.register(self.entry_node)
        from .navigation_history import NavigationHistory
        self.navigation=NavigationHistory(self.calculation.root)
        # Root value is the actual BoardOverview result, never a fixture value.
        self.nodes[self.root]['value']=forecast.village_win

    @classmethod
    def from_node(cls,node,*,role_order=None):
        """A continuation view over the same exact owner, not a saved-law rebase.

        View IDs/routes are local to this entry. Navigation occurrences own their
        parents and transports; the solver state can be shared independently.
        """
        from .exact import ROLES
        tree=cls.__new__(cls);tree.calculation=node._Node__calculation
        tree.data=node.data;tree.rules=tree.data.game_data.rules
        tree.strategy=tree.calculation._ClosedCalculation__strategy
        tree.engine=tree.calculation._ClosedCalculation__engine
        tree.role_order=tuple(ROLES if role_order is None else role_order)
        tree.snapshot=input_snapshot(tree.data)
        tree.nodes={};tree.sources={};tree.keys={};tree.values={};tree.traces={};tree.lock=RLock()
        tree.entry_node=node;tree.root=tree.register(node)
        from .navigation_history import NavigationHistory
        tree.navigation=NavigationHistory(node)
        # Recorded root input batches have already been applied. Replaying them
        # in a manual/continuation view would mix input snapshots with evidence.
        tree.input_updates=None
        return tree

    def equivalence(self,node,target=None):
        s=node.read();key=(s,target)
        if getattr(self.engine,'anonymous_nights',False):
            group=next((tuple(g) for g in node.groups if target in g),(target,)) if target is not None else None
            from .public_convergence import state_key
            return ('constructed-native',state_key(s),group)
        if key not in self.keys:
            self.keys[key]=canonical_key(*s,self.rules,self.strategy,target=target,physical=s.physical,max_mappings=120)
        return self.keys[key] or ('unshared',key)

    def register(self,node,route=()):
        s=node.read()
        from .public_convergence import state_key
        signature=state_key(s)
        if signature in self.sources:return self.sources[signature]
        key=str(len(self.nodes));self.sources[signature]=key
        self.nodes[key]={'node':node,'value':None,'actions':None,'reused':False,'route':tuple(route)}
        return key

    def value(self,key):
        row=self.nodes[key]
        if row['value'] is not None:return row['value']
        node=row['node'];s=node.read();canonical=self.equivalence(node)
        if canonical in self.values:row['value']=self.values[canonical];row['reused']=True
        else:
            with self.calculation._ClosedCalculation__kernel(),self.engine.group_scope(node.groups),node.relation_scope():
                from .closed_calculation import _forecast_scope
                _forecast_scope(s,self.engine)
                belief=getattr(self.engine,'anonymous_beliefs',{}).get(s)
                row['value']=self.engine.anonymous_values.value(belief) if belief is not None else self.engine.solve(*s,physical=s.physical)
            self.values[canonical]=row['value']
        return row['value']

    def candidates(self,node):
        e=self.engine;s=node.read();b=s.public
        if b.winner:return []
        rows=[]
        with self.calculation._ClosedCalculation__kernel(),e.group_scope(node.groups),node.relation_scope():
            if b.phase=='day':
                belief=getattr(e,'anonymous_beliefs',{}).get(s)
                scores=({p:v for group,v in e.anonymous_values.day_scores(e.anonymous_values.scalar(belief)) for p in group}
                        if belief is not None else dict(e.day_scores(b,s.public_state,s.past)))
                best=max(scores.values());selected=[t for t,v in scores.items() if e.strategy.day=='random' or v==best]
                legal=legal_targets(s.physical,self.rules,self.strategy)
                orbits=node.action_orbits() if getattr(e,'anonymous_nights',False) else tuple((p,) for p in legal)
                for orbit in orbits:
                    target=orbit[0]
                    rows.append({'node':node,'target':target,'orbit':orbit,'q_score':scores[target],
                        'policy_mass':F(sum(p in selected for p in orbit),len(selected)),
                        'fallback_mass':F(len(orbit),len(scores)),'information':'公開Q','owner_index':None})
            else:
                # Selection is from PUBLIC Q conditioned by actor information;
                # actual weights and child Boards come from the existing P split.
                choices=node.wolf_choices();owners={}
                for index,choice in enumerate(choices):owners.setdefault(choice.information,(choice.node,choice.information_mass,{},index))[2][choice.target]=choice.probability
                for info,(owned,mass,policy,owner_index) in owners.items():
                    own=owned.read();q_actor=info.condition_public(s.public_state)
                    with e.actor_scope(info):
                        for target in legal_targets(own.physical,self.rules,self.strategy):
                            score=e.act(b,s.public_state,s.past,target,q_actor,None,physical=physical_board(b,q_actor))
                            rows.append({'node':owned,'target':target,'q_score':score,
                                'policy_mass':mass*policy.get(target,F()),'fallback_mass':mass/F(len(legal_targets(own.physical,self.rules,self.strategy))),
                                'information':f'人狼本人I (初期人狼集合{info.initial_roster})','owner_index':owner_index})
        return rows

    def joint_trace(self,source,night,target):
        """Read the correlated realized actions from retained physical hypotheses.

        No marginal cross product: each complete pair carries its actual mass.
        A display equivalence is the existing full Q/P renaming check after
        conditioning P on that exact joint action. No solver node is replaced.
        """
        from .actor_information import condition_actor_state
        def event(h):
            wolves=tuple(p for p in range(1,source.public.player_count+1) if h.roles[0]&(1<<(p-1)))
            scans=tuple(sorted((a.player,a.target) for a in h.acquisitions if a.day==night+1))
            return wolves,scans
        events={}
        for h in source.private.hypotheses:events[event(h)]=events.get(event(h),F())+h.mass
        rows=[]
        for signature,probability in events.items():
            wolves,scans=signature
            law=condition_actor_state(source.private,lambda h:event(h)==signature)
            physical=physical_board(source.public,law,source.physical)
            key=canonical_key(source.public,source.public_state,source.past,law,source.observer,
                self.rules,self.strategy,target=target,physical=physical,max_mappings=120)
            text=('・'.join(f'{p}が{t}を占い' for p,t in scans) or '占い行動なし')+'｜'+','.join(map(str,wolves))+f'が{target}を襲撃'
            rows.append((key or ('named',source,signature,target),dict(wolves=list(wolves),scans=[list(s) for s in scans],target=target,label=text,probability=probability)))
        return rows

    def _expand_joint(self,key,actions):
        from .joint_action_kernel import group_outcomes,report_signature,compose
        from .seer_future_uniform import candidates
        record=self.nodes[key];node=record['node'];s=node.read();e=self.engine
        def names(players):
            values=list(sorted(players));return '['+','.join('('+str(p)+')' if p==values[0] else str(p) for p in values)+']から' if len(values)>1 else str(values[0])+'を'
        scans=[]
        for player in s.public.alive:
            if s.public.role_probability(player,'seer')==1:
                targets={t for h in s.private.hypotheses for t in candidates(h,player,s.public.alive)}
                scans.append(f'{player}が{names(targets)}占い')
        result=[]
        for action in actions:
            normalizer=action.policy_mass or action.fallback_mass;branches=[]
            for plan,weight,outcome in group_outcomes(e,action):
                child=node._joint_child(plan,outcome)
                variants=[];member_nodes=[]
                for original in plan.members:
                  for image_mass,image_mapping,_ in outcome.images:
                    member=replace(original,mapping=compose(image_mapping,original.mapping))
                    signature=report_signature(outcome.source,member.mapping) if outcome.report_index is not None else None
                    route=(*record['route'],(member.owner_index,member.target,outcome.outcome_index,signature))
                    if member.mapping==tuple(range(1,s.public.player_count+1)):
                        child_id=self.register(child,route)
                    else:
                        # Named images are recipes until a user requests one.
                        child_id=str(len(self.nodes))
                        lazy=DeferredNode(lambda route=route:self.nodes[self.restore(route)]['node'])
                        self.nodes[child_id]={'node':lazy,'value':None,'actions':None,'reused':False,'route':route}
                    actual=(member.policy_mass if action.policy_mass else member.fallback_mass)/normalizer*outcome.probability*image_mass
                    variants.append(dict(node=child_id,target=member.target,information='人狼本人情報',conditional_probability=str(outcome.probability*image_mass),mixture_probability=str(actual),transport=list(member.mapping)))
                    member_nodes.append((member,child_id,actual))
                representative=next((v['node'] for v in variants if v['target']==plan.target and v['transport']==list(range(1,s.public.player_count+1))),variants[0]['node'])
                traces=[]
                for _,event in self.joint_trace(outcome.source,s.public.day,plan.target):
                    members=[]
                    for member,child_id,actual in member_nodes:
                        wolves=[member.mapping[p-1] for p in event['wolves']]
                        acquired=[[member.mapping[p-1],member.mapping[t-1]] for p,t in event['scans']]
                        label='・'.join(f'{p}が{t}を占い' for p,t in acquired)+'｜'+','.join(map(str,wolves))+f'が{member.target}を襲撃'
                        members.append(dict(wolves=wolves,scans=acquired,target=member.target,label=label,node=child_id,probability=str(actual*event['probability'])))
                    traces.append(dict(label=members[0]['label'],probability=str(weight*outcome.probability*event['probability']),multiplicity=len(members),members=members))
                new=[r for r in outcome.source.past if r not in s.past]
                observation=('村勝利' if outcome.source.public.winner=='village' else '狼勝利' if outcome.source.public.winner=='wolf' else '継続')
                if new:observation+='・'+','.join(f'P{r.player}→P{r.target}{r.color}' for r in new)
                outcome_label=observation
                if len(new)==1:
                    color='白' if new[0].color=='white' else '黒'
                    outcome_label=color+'・'+('占い先が死亡' if new[0].target==plan.target else '別の対象が死亡')
                elif not new and outcome.source.public.winner is None:outcome_label='占い公開なし'
                branches.append(dict(node=representative,probability=str(weight*outcome.probability),variants=variants,observation=observation,outcome_label=outcome_label,joint_actions=traces))
            result.append(dict(targets=list(action.targets),label='・'.join(scans)+'｜人狼が'+names(action.targets)+'襲撃',grouped=True,
                multiplicity=sum(len(p.members) for p in action.plans),members=[dict(target=m.target,information='人狼本人情報',policy_mass=str(m.policy_mass)) for p in action.plans for m in p.members],
                q_score=None,selected=bool(action.policy_mass),policy_probability=str(action.policy_mass),branches=branches))
        record['actions']=result

    def _ability_columns(self,key):
        record=self.nodes[key];node=record['node'];source=node.read()
        if source.public.phase!='night' or source.public.winner:return
        if any(b.get('trace_pending') for a in record['actions'] or [] for b in a['branches']):
            record['ability_pending']='完全な占い履歴を復元できないため、既存の厳密な同時行動を表示します。'
            return
        from .joint_action_kernel import report_signature,compose
        metadata={}
        n=source.public.player_count
        def canonical(scans):
            mapping={};used=set()
            for p in (*[a for a,t in scans],*[t for a,t in scans]):
                if p in mapping:continue
                group=next((g for g in node.groups if p in g),(p,))
                target=next(x for x in group if x not in used);mapping[p]=target;used.add(target)
            for group in node.groups:
                for p,t in zip((p for p in group if p not in mapping),(p for p in group if p not in used)):mapping[p]=t
            return tuple(mapping.get(p,p) for p in range(1,n+1))
        def event_key(member,mapping):
            child,transport=metadata[id(member)]
            return (tuple(sorted(mapping[p-1] for p in member['wolves'])),tuple(sorted((mapping[a-1],mapping[t-1]) for a,t in member['scans'])),mapping[member['target']-1],repr(report_signature(child,compose(transport,mapping))))
        identity=tuple(range(1,n+1));entries=[];lookup={}
        for action in record['actions'] or []:
            for branch in action['branches']:
                for trace in branch.get('joint_actions',[]):
                    for member in trace['members']:
                        variant=next((v for v in branch['variants'] if v['node']==member['node']),{})
                        metadata[id(member)]=(self.nodes[branch['node']]['node'].read(),tuple(variant.get('transport',identity)))
                        entries.append((action,branch,member));lookup.setdefault(event_key(member,identity),member)
        scans={};conditioned={}
        for action,branch,member in entries:
            mapping=canonical(member['scans']);signature=event_key(member,mapping)
            actual=lookup.get(signature)
            if actual is None:signature=event_key(member,identity);actual=member
            wolves,acquisitions,victim,public_signature=signature
            scan=scans.setdefault(acquisitions,dict(mass=F(),targets={},attacks={}))
            for a,t in member['scans']:scan['targets'].setdefault(a,set()).add(t)
            weight=F(member['probability']);policy=F(action['policy_probability']);mass=policy*weight
            scan['mass']+=mass
            attack=scan['attacks'].setdefault(victim,dict(mass=F(),counter=F(),families={},outcomes={}))
            attack['mass']+=mass;attack['counter']+=weight
            family=tuple(action['targets']);attack['families'][family]=True
            outcome=attack['outcomes'].setdefault(signature,dict(mass=F(),counter=F(),member=actual,label=branch.get('outcome_label',branch['observation'])))
            outcome['mass']+=mass;outcome['counter']+=weight
        result=[]
        for acquisitions,scan in scans.items():
            parts=[]
            for actor,target in acquisitions:
                group=next((g for g in node.groups if target in g),(target,))
                targets=sorted({t for a,t in (pair for _,_,m in entries for pair in m['scans']) if a==actor and t in group})
                label='['+','.join('('+str(t)+')' if t==target else str(t) for t in targets)+']から' if len(targets)>1 else str(target)+'を'
                owner=str(actor) if source.public.role_probability(actor,'seer')==1 else '占い師'
                parts.append(f'{owner}が{label}占い')
            attacks=[]
            for victim,attack in sorted(scan['attacks'].items()):
                branches=[];total=attack['mass'] or attack['counter']
                for signature,outcome in attack['outcomes'].items():
                    wolves,acquired,_,public_signature=signature
                    selected=outcome['member'];cache=(selected['node'],wolves,acquired)
                    if cache not in conditioned:
                        base=self.nodes[selected['node']]['node'];full=base._with_full_trace()
                        child=full._select_physical('joint',(source.public.day,wolves,acquired))
                        route=self.nodes[selected['node']]['route']
                        if full.read()!=base.read():route=(*route,{'full_trace':True})
                        child_id=self.register(child,(*route,{'physical':'joint','value':(source.public.day,wolves,acquired)}));conditioned[cache]=child_id
                    branches.append(dict(node=conditioned[cache],probability=str((outcome['mass'] if attack['mass'] else outcome['counter'])/total),mass=str(outcome['mass']),counter=str(outcome['counter']),observation=outcome['label']))
                family_total=sum(other['counter'] for other in scan['attacks'].values() if set(other['families'])&set(attack['families']))
                attacks.append(dict(label=f'人狼が{victim}を襲撃',target=victim,targets=[victim],mass=str(attack['mass']),counter=str(attack['counter']),policy_probability=str(attack['mass']/scan['mass'] if scan['mass'] else F()),conditional_probability=str(attack['counter']/family_total),branches=branches))
            result.append(dict(label='・'.join(parts) if parts else '占いなし',scans=[list(p) for p in acquisitions],probability=str(scan['mass']),attacks=attacks,simultaneous=True))
        from .ability_factorization import factor
        record['ability_choices']=factor(self,node,result)

    def _public_night_bundles(self,key):
        from .public_convergence import public_observation_orbits,public_night_observations,digest
        record=self.nodes[key]
        if 'public_bundles' in record:return record['public_bundles']
        node=record['node'];program=node._night_program();groups=program.groups;result={}
        with self.calculation._ClosedCalculation__kernel(),self.engine.group_scope(node.groups),node.relation_scope():
            if getattr(program,'belief_flow',None) is not None:
                from .anonymous_materialization import source as named_boundary
                from .public_convergence import public_transport,transport_source
                flow=program.belief_flow;templates={}
                for leaf in program.leaves:
                    mapping=public_transport(node.read(),leaf.source,groups)
                    moved=transport_source(leaf.source,mapping)
                    templates.setdefault((mapping[leaf.target-1],moved.public.winner),moved)
                for observation in flow.observations():
                    for counter in (False,True):
                        try:reach,owned=flow.branch(observation,counter=counter)
                        except ValueError as error:
                            if str(error)!='Anonymous observation has zero support':raise
                            continue
                        source=named_boundary(owned,templates[observation])
                        self.engine.anonymous_beliefs[source]=owned
                        public=digest(source);entry=result.setdefault(public,dict(target=observation[0],sources={},owned={},flow=flow,observation=observation))
                        entry['sources'][counter]=(reach,source);entry['owned'][counter]=owned
            else:
                for counter in (False,True):
                    for reach,source,target in public_night_observations(self.engine,node.read(),groups,counter=counter):
                        public=digest(source);entry=result.setdefault(public,dict(target=target,sources={}))
                        entry['sources'][counter]=(reach,source)
            for public,entry in result.items():
                counter=False if False in entry['sources'] else True
                reach,source=entry['sources'][counter]
                child=node._public_night(source,entry['target'],public,groups,counter=counter)
                route=(*record['route'],{'public_night':dict(target=entry['target'],public=public,prefix=[],counter=counter)})
                child_key=self.register(child,route);entry['node']=child_key
                self.nodes[child_key].update(public_bundle=True,public_digest=public,public_reach=str(reach if not counter else F()),counterfactual=counter,hidden_contexts=[])
                self.nodes[child_key]['distribution_origin']=(key,program,public)
        record['public_bundles']=result
        if any(step.kind=='publication' for leaf in program.leaves for step in leaf.steps):
            from .tree_public_updates import state_summary,publication_label
            with self.calculation._ClosedCalculation__kernel(),self.engine.group_scope(node.groups),node.relation_scope():
                arrivals={}
                for counter in (False,True):
                    for reach,before,target in public_night_observations(self.engine,node.read(),groups,counter=counter,publish=False):
                        if before.public.winner:continue
                        total=reach
                        updates=[]
                        for public,entry in result.items():
                            if entry['target']!=target or counter not in entry['sources']:continue
                            weight,after=entry['sources'][counter]
                            if after.public.winner!=before.public.winner:continue
                            updates.append(dict(node=entry['node'],probability=str(weight/total),label=publication_label(before,after)))
                        if not updates:continue
                        identity='arrival:'+key+':'+digest(before)+':'+str(counter)
                        value=sum((F(u['probability'])*self.value(u['node']) for u in updates),F())
                        arrival=dict(id=identity,state=state_summary(before.public,before.private,identity,self.data.game_data,self.role_order,value=value,past=before.past),updates=updates,kind='generated_updates')
                        arrival_node=node._public_arrival(before,target,digest(before),groups,counter)
                        selector=dict(public_arrival=dict(target=target,public=digest(before),counter=counter))
                        arrival_key='start:'+identity
                        self.nodes[arrival_key]=dict(node=arrival_node,value=value,actions=[],reused=False,route=(*record['route'],selector),public_bundle=True,day_start=True,public_updates=updates)
                        arrival['node']=arrival_key
                        record.setdefault('arrival_selectors',{})[(target,digest(before),counter)]=arrival_key
                        from .public_convergence import legacy_digest
                        record['arrival_selectors'][(target,legacy_digest(before),counter)]=arrival_key
                        arrivals[identity]=arrival
                        record.setdefault('arrival_sources',{})[identity]=before
                        for update in updates:
                            record_after=self.nodes[update['node']]
                            if 'day_arrival' not in record_after or not counter:record_after['day_arrival']=arrival
                record['day_arrivals']=arrivals
        return result

    def _public_context(self,key,public,prefix,counter=False):
        from .public_convergence import condition_prefix
        from dataclasses import asdict
        bundles=self._public_night_bundles(key);entry=bundles[public];mass,source=entry['sources'][counter]
        if 'owned' in entry:
            from .anonymous_materialization import source as named_boundary
            relative,owned=entry['flow'].branch(entry['observation'],prefix,counter)
            source=named_boundary(owned,source);self.engine.anonymous_beliefs[source]=owned
        elif prefix:
            relative,source=condition_prefix(source,self.nodes[key]['node'].read(),self.nodes[key]['node']._night_program().groups,prefix)
        child=self.nodes[key]['node']._public_night(source,entry['target'],public,self.nodes[key]['node']._night_program().groups,prefix,counter)
        route=(*self.nodes[key]['route'],{'public_night':dict(target=entry['target'],public=public,prefix=[asdict(step) for step in prefix],counter=counter)})
        child_key=self.register(child,route)
        self.nodes[child_key]['public_parent_bundle']=entry['node']
        if counter:self.nodes[child_key]['counterfactual']=True
        contexts=self.nodes[entry['node']]['hidden_contexts']
        if child_key!=entry['node'] and not any(row['node']==child_key for row in contexts):
            label=' → '.join(step.label() for step in prefix if step.kind in ('seer_result','wolf_target'))
            contexts.append(dict(node=child_key,label=(label or '経路')+(' · 方策0' if counter else '')))
        return child_key

    def _stage_rows(self,key):
        row=self.nodes[key]
        if 'night_stages' in row:return row['night_stages']
        from .night_program import NightStage
        node=row['node'];program=node._night_program()
        if program is None:return None
        def leaf_row(leaf):
            child=node._stage_child(leaf)
            route=(*row['route'],(leaf.owner_index,leaf.target,leaf.outcome_index,leaf.report),{'physical':'joint','value':(node.read().public.day,leaf.wolves,leaf.scans)})
            return self.register(child,route)
        symbolic=getattr(program,'method',None)=='anonymous-relational-v1'
        native=symbolic or getattr(program,'method',None)=='role-staged-exact-v1'
        base_key=row.get('public_parent',key)
        bundles=self._public_night_bundles(base_key) if native else None
        built={}
        def build(stage):
            cache=(tuple(id(leaf) for leaf in stage.leaves),stage.prefix)
            if cache in built:return built[cache]
            if stage.terminal:
                total=stage.mass or stage.counter
                if native:
                    from .public_convergence import public_transport,transport_source,digest
                    grouped={}
                    for mass,counter,leaf,images in stage.outcomes():
                        mapping=public_transport(self.nodes[base_key]['node'].read(),leaf.source,self.nodes[base_key]['node']._night_program().groups)
                        public=digest(transport_source(leaf.source,mapping));entry=grouped.setdefault(public,F());grouped[public]=entry+(mass if stage.mass else counter)
                    return dict(leaves=[dict(node=bundles[public]['node'],context_node=self._public_context(base_key,public,stage.prefix,not bool(stage.mass)) if symbolic and getattr(program,'private_contexts',True) else None,probability=str(mass/total),variants=[]) for public,mass in grouped.items()])
                return dict(leaves=[dict(node=leaf_row(leaf),probability=str((mass if stage.mass else counter)/total),variants=[dict(node=leaf_row(image),transport=list(mapping)) for image,mapping in images]) for mass,counter,leaf,images in stage.outcomes()])
            branches=[]
            for branch in stage.branches():
                step=branch.step
                if getattr(program,'method',None)=='anonymous-relational-v1':
                    from dataclasses import asdict
                    label=step.label();symbol=lambda x:None if x is None else asdict(x)
                    mediums=self.data.game_data.mediums;seers=self.data.game_data.seers;hunters=self.data.game_data.hunters;prefix=stage.prefix
                    stage_kind=lambda s:s.value if s.kind=='ability_dead' else s.kind
                    effective=stage_kind(step)
                    position=(sum(stage_kind(s)=='medium_result' for s in prefix) if effective=='medium_result' else mediums+sum(stage_kind(s) in ('seer_target','seer_result') for s in prefix) if effective in ('seer_target','seer_result') else mediums+2*seers+sum(stage_kind(s)=='guard_target' for s in prefix) if effective=='guard_target' else mediums+2*seers+hunters+(step.kind=='death_notice')+(2 if step.kind=='publication' else 0))
                    branches.append(dict(stage_column=position,public_fact=step.public_fact,kind=step.kind,actor=None if step.actor is None else step.actor.index+1,actors=[x.index+1 for x in step.actors],value=step.value,label=label,targets=[],symbols=dict(actor=symbol(step.actor),target=symbol(step.target) if hasattr(step.target,'members') else None,actors=[symbol(x) for x in step.actors]),probability=str(branch.probability),policy_probability=str(branch.policy_probability),counter_probability=str(branch.counter_probability),mass=str(branch.mass),private=step.kind not in ('death_notice','publication'),public_observation=step.kind in ('death_notice','publication'),visible_to=list(step.visible_to),children=build(branch.state),images=[]))
                else:
                    from .ability_labels import stage_label
                    label,actor_groups,joint_choices=stage_label(branch)
                    prefix=stage.prefix;role_column=None
                    if native:
                        mediums=self.data.game_data.mediums;seers=self.data.game_data.seers;hunters=self.data.game_data.hunters
                        stage_kind=lambda s:s.value if s.kind=='ability_dead' else s.kind
                        effective=stage_kind(step)
                        role_column=(sum(stage_kind(s)=='medium_result' for s in prefix) if effective=='medium_result' else mediums+sum(stage_kind(s) in ('seer_target','seer_result') for s in prefix) if effective in ('seer_target','seer_result') else mediums+2*seers+sum(stage_kind(s)=='guard_target' for s in prefix) if effective=='guard_target' else mediums+2*seers+hunters+(step.kind=='death_notice')+(2 if step.kind=='publication' else 0))
                    branches.append(dict(stage_column=role_column,kind=step.kind,actor=step.actor,actor_groups=actor_groups,joint_choices=joint_choices,actors=list(step.actors),value=step.value,label=label,targets=list(branch.targets),probability=str(branch.probability),policy_probability=str(branch.policy_probability),counter_probability=str(branch.counter_probability),mass=str(branch.mass),private=step.kind not in ('death_notice','publication'),public_observation=step.kind in ('death_notice','publication'),visible_to=list(step.visible_to),multiplicity=len(branch.images),children=build(branch.state),images=[dict(transport=list(mapping),nodes=[leaf_row(leaf) for leaf in leaves],children=None if mapping==program.identity else build(NightStage(program,leaves,(*stage.prefix,named)))) for named,leaves,mapping in branch.images]))
            result=dict(branches=branches);built[cache]=result
            return result
        result=build(program.root);result['method']=getattr(program,'method','verified-named');result['stats']=getattr(program,'stats',{});row['night_stages']=result;return result

    def expand(self,key):
        record=self.nodes[key]
        if record['actions'] is not None:return
        node=record['node'];groups={}
        if node.read().public.phase=='night' and not node.read().public.winner:
            stages=self._stage_rows(key)
            if stages and stages.get('method') in ('anonymous-relational-v1','role-staged-exact-v1'):
                record['actions']=[];return
        with self.calculation._ClosedCalculation__kernel():
            joint=node._joint_actions()
            if joint is not None:
                self._expand_joint(key,joint)
                self._ability_columns(key)
                return
        for row in self.candidates(node):groups.setdefault(self.equivalence(row['node'],row['target']),[]).append(row)
        choices=[]
        for members in groups.values():
            policy_mass=sum((r['policy_mass'] for r in members),F())
            normalizer=policy_mass or sum((r['fallback_mass'] for r in members),F())
            branches={};named=[]
            for member in members:
                tick();origin=member['node'];s=origin.read();target=member['target']
                weight=(member['policy_mass'] if policy_mass else member['fallback_mass'])/normalizer
                named.extend({'target':p,'information':member['information'],'policy_mass':str(member['policy_mass']/len(member.get('orbit',(target,))))} for p in member.get('orbit',(target,)))
                if not weight:continue
                for outcome_index,physical in enumerate(origin.action(target)):
                    after=physical.node
                    reports=after.reports() if s.public.phase=='night' and after.read().public.winner is None else None
                    outcomes=[(r.probability,r.node,i) for i,r in enumerate(reports)] if reports else [(F(1),after,None)]
                    for report_mass,child,report_index in outcomes:
                        source=child.read();chance=physical.probability*report_mass
                        route=(*record['route'],(member['owner_index'],target,outcome_index,report_index))
                        child_id=self.register(child,route);canonical=self.equivalence(child)
                        observation=('村勝利' if source.public.winner=='village' else '狼勝利' if source.public.winner=='wolf' else '継続')
                        new_reports=[r for r in source.past if r not in s.past]
                        if new_reports:observation+='・'+','.join(f'P{r.player}→P{r.target}{r.color}' for r in new_reports)
                        bucket=branches.setdefault(canonical,{'node':child_id,'probability':F(),'variants':[],'observation':observation,'joint_actions':{}})
                        bucket['probability']+=weight*chance
                        bucket['variants'].append({'node':child_id,'target':target,'information':member['information'],
                            'conditional_probability':str(chance),'mixture_probability':str(weight*chance)})
                        if s.public.phase=='night':
                            if child_id not in self.traces:
                                from .action_tree_trace import trace_source
                                self.traces[child_id]=trace_source(child)
                            trace_state,trace_pending=self.traces[child_id]
                            bucket['trace_pending']=trace_pending
                            for trace_key,event in self.joint_trace(trace_state,s.public.day,target):
                                if trace_pending:event['label']=event['label'].replace('占い行動なし','占い履歴未表示')
                                trace=bucket['joint_actions'].setdefault(trace_key,dict(label=event['label'],probability=F(),members=[]))
                                contribution=weight*chance*event['probability'];trace['probability']+=contribution
                                trace['members'].append({**event,'node':child_id,'probability':str(contribution)})
            target_ids=sorted({p for r in members for p in r.get('orbit',(r['target'],))})
            for branch in branches.values():
                branch['probability']=str(branch['probability'])
                branch['joint_actions']=list(branch['joint_actions'].values())
                for trace in branch['joint_actions']:
                    trace['probability']=str(trace['probability'])
                    trace['multiplicity']=len(trace['members'])
            choices.append({'targets':target_ids,'label':('処刑' if node.read().public.phase=='day' else '襲撃')+' '+ '/'.join('P'+str(p) for p in target_ids),
                'multiplicity':sum(len(r.get('orbit',(r['target'],))) for r in members),'members':named,'q_score':str(members[0]['q_score']),
                'selected':bool(policy_mass),'policy_probability':str(policy_mass),'branches':list(branches.values())})
        record['actions']=choices
        with self.calculation._ClosedCalculation__kernel():self._ability_columns(key)

    def restore(self,route):
        """Reconstruct a named physical path only through common generators."""
        if type(route) not in (list,tuple) or len(route)>6*self.data.game_data.players+1:raise ValueError('Invalid Current path')
        node=self.entry_node;prefix=();view_key=None
        for step in route:
            view_key=None
            if type(step)is dict:
                if set(step)=={'public_arrival'}:
                    selector=step['public_arrival'];base=self.register(node,prefix);self._public_night_bundles(base)
                    view_key=self.nodes[base].get('arrival_selectors',{}).get((selector['target'],selector['public'],selector.get('counter',False)))
                    if view_key is None:raise ValueError('Public arrival unavailable')
                    node=self.nodes[view_key]['node']
                elif set(step)=={'public_night'}:
                    from .anonymous_night import Symbol,SymbolStep
                    selector=step['public_night'];base=self.register(node,prefix);bundles=self._public_night_bundles(base)
                    public=selector['public']
                    if public not in bundles:
                        from .public_convergence import matches_digest
                        public=next((code for code,entry in bundles.items() if any(matches_digest(source,public) for mass,source in entry['sources'].values())),public)
                    if public not in bundles or selector['target']!=bundles[public]['target']:raise ValueError('Public night selector unavailable')
                    def symbol(value):return None if value is None else Symbol(value['index'],tuple(value['members']))
                    pattern=tuple(SymbolStep(r['kind'],symbol(r['actor']),symbol(r['target']) if type(r['target'])is dict else r['target'],tuple(symbol(a) for a in r['actors']),r.get('public_fact')) for r in selector['prefix'])
                    selected=self._public_context(base,public,pattern,selector.get('counter',False)) if pattern else bundles[public]['node']
                    node=self.nodes[selected]['node']
                elif step=={'full_trace':True}:node=node._with_full_trace()
                elif set(step)=={'physical','value'}:node=node._select_physical(step['physical'],step['value'])
                else:raise ValueError('Invalid physical selector')
                prefix=(*prefix,step)
                if view_key is None:self.register(node,prefix)
                continue
            if type(step) not in (list,tuple) or len(step)!=4:raise ValueError('Invalid Current step')
            owner,target,outcome,report=step
            if type(target)is not int or any(v is not None and (type(v)is not int or v<0) for v in (owner,outcome)) or report is not None and (type(report) not in (int,dict) or type(report)is int and report<0):raise ValueError('Invalid Current selector')
            if outcome is None:raise ValueError('Physical outcome required')
            try:
                if owner is not None:node=node.wolf_choices()[owner].node
                node=node.action(target)[outcome].node
                if type(report)is dict:
                    from .joint_action_kernel import report_signature
                    if set(report)!={'seer','medium'}:raise ValueError('Invalid report selector')
                    node=next(r.node for r in node.reports() if report_signature(r.node.read())==report)
                elif report is not None:node=node.reports()[report].node
            except (IndexError,KeyError,StopIteration) as exc:raise ValueError('Current path unavailable') from exc
            prefix=(*prefix,tuple(step));self.register(node,prefix)
        return view_key if view_key is not None else self.register(node,prefix)

    def route(self,key):
        with self.lock:return [dict(step) if type(step)is dict else list(step) for step in self.nodes[key]['route']]

    def _composition_rows(self,key):
        row=self.nodes[key]
        if 'composition_rows' in row:return row['composition_rows']
        node=row['node'];result=[];parts=node._compositions()
        for composition,probability in parts:
            w,m,seer,h,v=composition
            label=composition_label(composition,self.data.game_data,self.role_order)
            child=key if len(parts)==1 else self.register(node._select_physical('composition',composition),(*row['route'],{'physical':'composition','value':composition}))
            if child!=key:self.nodes[child]['public_parent']=row.get('public_parent',key)
            result.append(dict(node=child,counts=dict(wolves=w,mediums=m,seers=seer,hunters=h,citizens=v),label=label,probability=str(probability)))
        row['composition_rows']=result;return result

    def public_current(self,key):
        row=self.nodes[key]
        if row.get('public_parent_bundle') and not row.get('public_bundle'):return False
        for step in row['route']:
            if type(step)is dict:
                if 'physical' in step:return False
                if step.get('public_night',{}).get('prefix'):return False
            elif len(step)==4 and step[0] is not None:return False
        return True

    def distribution(self,key,*,names=None):
        """Inline analysis only; no navigation ids or changed public state."""
        with self.lock,self.calculation._ClosedCalculation__kernel():
            row=self.nodes[key]
            cache='distribution' if names is None else ('distribution',names.forward)
            if cache in row:return row[cache]
            from .physical_selection import counts
            from .anonymous_relations import alias
            node=row['node'];source=node.read();events=[]
            origin=row.get('distribution_origin')
            program=node._night_program() if not origin and source.public.phase=='night' and not source.public.winner else None
            if origin:
                base,program,public=origin
                from .public_convergence import public_transport,transport_source,digest
            if program is not None:
                for leaf in program.leaves:
                    if origin:
                        mapping=public_transport(self.nodes[base]['node'].read(),leaf.source,program.groups)
                        if digest(transport_source(leaf.source,mapping))!=public:continue
                    mass=leaf.counter if row.get('counterfactual') else leaf.mass
                    if not mass:continue
                    composition=counts(leaf.source.private.hypotheses[0],leaf.source.public.alive if origin else source.public.alive)
                    results=[];actions=[]
                    for step in leaf.steps:
                        if step.kind=='seer_result':
                            actor=step.actor.index if hasattr(step.actor,'index') else step.actor
                            results.append((actor,step.target if hasattr(step,'target') else step.value))
                        elif step.kind=='medium_result':
                            if hasattr(step,'label'):
                                if names is None:label=step.label()
                                else:
                                    from .anonymous_night import Symbol,SymbolStep
                                    sym=lambda x:Symbol(x.index,tuple(names.display(p) for p in x.members))
                                    label=SymbolStep(step.kind,sym(step.actor),sym(step.target),public_fact=step.public_fact).label()
                                results.append(('medium',label))
                            else:results.append(('medium',step.actor,step.value[0],step.value[1]))
                        elif step.kind in ('seer_target','guard_target','wolf_target'):
                            if hasattr(step,'label'):
                                if names is None:actions.append(step.label())
                                else:
                                    from .anonymous_night import Symbol,SymbolStep
                                    sym=lambda x:Symbol(x.index,tuple(names.display(p) for p in x.members))
                                    actions.append(SymbolStep(step.kind,None if step.actor is None else sym(step.actor),sym(step.target) if hasattr(step.target,'members') else step.target,tuple(sym(a) for a in step.actors)).label())
                            else:
                                display=lambda p:names.display(p) if names is not None else p
                                owner='と'.join(str(display(p)) for p in step.actors) if step.kind=='wolf_target' else str(display(step.actor))
                                actions.append(owner+'が'+str(display(step.value))+('を占い' if step.kind=='seer_target' else 'を護衛' if step.kind=='guard_target' else 'を襲撃'))
                    events.append((composition,tuple(results),tuple(actions),mass))
            output=[]
            for index,part in enumerate(self._composition_rows(key)):
                composition=(part['counts']['wolves'],part['counts']['mediums'],part['counts']['seers'],part['counts']['hunters'],part['counts']['citizens'])
                rows=[(results,actions,mass) for c,results,actions,mass in events if c==composition]
                total=sum((mass for r,a,mass in rows),F());children=[];buckets={}
                for results,actions,mass in rows:buckets.setdefault(results,[]).append((actions,mass))
                for result_index,(results,paths) in enumerate(buckets.items()):
                    subtotal=sum((mass for a,mass in paths),F());grouped={}
                    for actions,mass in paths:grouped[actions]=grouped.get(actions,F())+mass
                    leaves=[dict(id=f'{index}/r{result_index}/a{i}',label=' → '.join(actions),probability=str(mass/subtotal),children=[]) for i,(actions,mass) in enumerate(grouped.items())]
                    if not results and len(buckets)==1:children=leaves
                    else:
                        colors=lambda color:'白' if color=='white' else '黒'
                        if any(r[0]=='medium' for r in results):
                            display=lambda p:names.display(p) if names is not None else p
                            label='・'.join(('霊能結果：'+(r[1] if len(r)==2 else str(display(r[1]))+'→'+str(display(r[2]))+colors(r[3]))) if r[0]=='medium' else ('占い結果：'+alias(r[0])+' '+colors(r[1])) for r in results)
                        else:label='占いなし' if not results else ('占い結果：'+colors(results[0][1]) if len(results)==1 else '占い結果：'+'・'.join(alias(actor)+' '+colors(color) for actor,color in results))
                        children.append(dict(id=f'{index}/r{result_index}',label=label,probability=str(subtotal/total),children=leaves))
                output.append(dict(id=str(index),label=part['label'],probability=part['probability'],village_win=str(self.value(part['node'])),children=children))
            row[cache]=output;return output

    def summary(self,key,actions=False):
        row=self.nodes[key];node=row['node'];s=node.read();b=s.public;value=self.value(key)
        from .board_flow import BoardFacts
        point=BoardFacts.from_inputs(self.data.game_data,{'history':[asdict(e) for e in b.history]})
        certificate=node.win_certificate()
        return {'snapshot':self.snapshot,'node':key,'day':b.day,'phase':b.phase,'column_day':point.day if b.winner else b.day,'column_phase':point.phase if b.winner else b.phase,'alive':list(b.alive),'winner':b.winner,
            'day_arrival':row.get('day_arrival'),'day_start':row.get('day_start',False),'public_updates':row.get('public_updates'),'public_current':self.public_current(key),'public_claims':list(b.claims),'native_mode':getattr(self.engine,'anonymous_nights',False),'counterfactual':row.get('counterfactual',False),'public_bundle':row.get('public_bundle',False),'public_parent_bundle':row.get('public_parent_bundle'),'hidden_contexts':list(row.get('hidden_contexts',[])),'public_reach':row.get('public_reach'),
            'viewpoint':'公開Qで方針決定 / 物理Pで評価'+('（本人条件付き枝）' if s.private!=s.public_state else ''),
            'village_win':str(value),'wolf_win':str(1-value),'evaluation':'computed',
            'win_certificate':asdict(certificate) if certificate else None,
            'cutoff_marker':certificate.marker(point.day) if certificate and row['actions'] is None else None,
            'expansion':'computed' if row['actions'] is not None or b.winner else 'pending','reused':row['reused'],
            'mode':getattr(self.strategy,b.phase),'rules':asdict(self.rules),'policy':asdict(self.strategy),
            'history':[asdict(e) for e in b.history],'reports':[asdict(r) for r in s.past],
            'players':[{'player':p,'alive':p in b.alive,'wolf_probability':str(b.wolf_probability(p)),
                'seer_probability':str(b.role_probability(p,'seer')),
                'physical_wolf_probability':str(sum((h.mass for h in s.private.hypotheses if h.roles[0]&(1<<(p-1))),F()))} for p in range(1,b.player_count+1)],
            'compositions':self._composition_rows(key),'night_stages':row.get('night_stages'),'stage_roles':dict(seers=self.data.game_data.seers,mediums=self.data.game_data.mediums,hunters=self.data.game_data.hunters),'ability_choices':row.get('ability_choices'),'ability_pending':row.get('ability_pending'),'actions':row['actions'] if actions else None,'fixture':f'{self.data.game_data.players} players / {self.data.game_data.seers} seers / {self.data.game_data.wolves} wolves',
            'method':'完全なQ/P・履歴・物理枝の既存の名前付替え同値でまとめます。全ての成員Boardを選択できます。'}

    def read(self,key,expand=False):
        with self.lock:
            if key not in self.nodes:raise KeyError(key)
            if expand and not self.nodes[key]['node'].win_certificate():self.expand(key)
            result=self.summary(key,True);items={};pending=[key];seen=set()
            while pending:
                parent=pending.pop()
                if parent in seen:continue
                seen.add(parent)
                for update in self.nodes[parent].get('public_updates') or ():
                    child=update['node'];items[child]=self.summary(child,True);pending.append(child)
                arrival=self.nodes[parent].get('day_arrival')
                if arrival and arrival.get('node'):
                    child=arrival['node'];items[child]=self.summary(child,True);pending.append(child)
                for composition in self._composition_rows(parent):
                    child=composition['node']
                    if child!=parent:items[child]=self.summary(child,True);pending.append(child)
                for choice in self.nodes[parent].get('ability_choices') or []:
                    for attack in choice['attacks']:
                        for branch in attack['branches']:
                            for child in [branch['node'],*[v['node'] for v in branch.get('variants',[])]]:
                                items[child]=self.summary(child,True);pending.append(child)
                stage_pending=[self.nodes[parent].get('night_stages')]
                while stage_pending:
                    stage=stage_pending.pop()
                    if not stage:continue
                    for branch in stage.get('branches',[]):
                        stage_pending.append(branch['children'])
                        for image in branch['images']:
                            for child in image['nodes']:items[child]=self.summary(child,True);pending.append(child)
                    for leaf in stage.get('leaves',[]):
                        child=leaf['node'];items[child]=self.summary(child,True);pending.append(child)
                for choice in self.nodes[parent]['actions'] or []:
                    for branch in choice['branches']:
                        child=branch['node'];items[child]=self.summary(child,True);pending.append(child)
            result['items']=items
            if key==self.root:
                if not hasattr(self,'input_updates'):
                    from .tree_public_updates import input_timeline
                    self.input_updates=input_timeline(self.calculation._ClosedCalculation__origin_data,self.role_order)
                result['input_timeline']=self.input_updates
            return result
