"""One pending publication day, <=2 exchangeable reporters, <=1 fake per world.

Candidate primitives and complete posterior weights use the existing laws.
Only public category/equality patterns are generated before named restoration.
No player number or execution/bite pair participates in pattern selection.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from itertools import combinations_with_replacement,permutations,product
from math import perm,prod
from collections import Counter
from .cut_out_joint_night_prototype import move_law,move_board
from .cut_out_inherited_groups import InheritedGroupRegistry,InheritedGroups
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.morning_publications import GeneratedPublication,plausible_fake_options,fake_backlog_options,public_report_branches
from werewolf.seer_future_uniform import true_reports,FuturePending
from werewolf.seer_acquisition import normalize
from werewolf.board_future import same_role_board
from werewolf.exact import report_actions


@dataclass(frozen=True)
class PublicationPattern:
    reporters:tuple
    groups:tuple
    categories:tuple
    endpoints:tuple
    reporter_factor:int
    multiplicity:int
    branch:GeneratedPublication


def primitive_laws(board,state,past,reporters,fake_policy):
    if tuple(fake_policy) not in (('uniform',),('noncontradictory','uniform')):
        raise Pending('publication_configured_fake_law_unproved')
    generator=plausible_fake_options if 'noncontradictory' in fake_policy else fake_backlog_options
    fake={};candidates={}
    for p in reporters:
        truth={true_reports(h,past,board.alive,board.claims,board.day) for h in state.hypotheses if h.roles[2]&(1<<(p-1))}
        choices=generator(state,(p,),past) if any(not h.roles[2]&(1<<(p-1)) for h in state.hypotheses) else ()
        if isinstance(choices,FuturePending):raise Pending(choices.reason)
        fake[p]=dict(choices)
        rows=truth|set(fake[p])
        if any(len(row)!=1 or row[0].player!=p or row[0].acquired_day!=board.day or row[0].published_day!=board.day for row in rows):
            raise Pending('publication_exactly_one_pending_report_day_required')
        candidates[p]=rows
    return candidates,fake


def require_groups(board,state,past,groups):
    if board.phase!='day' or board.initial_hunter_count or board.initial_seer_count!=1 or len(state.rosters)!=board.day:
        raise Pending('publication_day_S1_H0_scope')
    if report_actions(board):raise Pending('publication_medium_observation_must_precede_seer')
    if state.public_roles!=tuple(sorted(board.worlds)) or any(h.guards for h in state.hypotheses):
        raise Pending('publication_complete_public_law_required')
    if tuple(sorted(p for group in groups for p in group))!=tuple(range(1,board.player_count+1)):
        raise Pending('publication_groups_must_partition_players')
    for h in state.hypotheses:
        if h.roles[2].bit_count()!=1:raise Pending('publication_single_true_owner_required')
        for a in h.acquisitions:
            if (a.day>len(state.rosters) or a.player not in state.rosters[a.day-1] or
                not h.roles[2]&(1<<(a.player-1)) or a.color!=('black' if h.roles[0]&(1<<(a.target-1)) else 'white')):
                raise Pending('publication_secret_acquisition_history_inconsistent')
        for row in past:
            if h.roles[2]&(1<<(row.player-1)) and not any(a.day==row.acquired_day and a.player==row.player and a.target==row.target and a.color==row.color for a in h.acquisitions):
                raise Pending('publication_past_true_report_inconsistent')
    reporters=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    if len(reporters)>2 or reporters and reporters not in groups:
        raise Pending('publication_reporters_must_be_one_certified_group_size_at_most_two')
    if any(sum(not h.roles[2]&(1<<(p-1)) for p in reporters)>1 for h in state.hypotheses):
        raise Pending('publication_multiple_fake_joint_law_unselected')
    for group in groups:
        for p in group[1:]:
            mapping=list(range(1,board.player_count+1));mapping[group[0]-1],mapping[p-1]=p,group[0];mapping=tuple(mapping)
            history=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in past))
            if move_law(state,mapping)!=state or not same_role_board(move_board(board,state,mapping),board) or history!=past:
                raise Pending('publication_full_public_history_group_symmetry_required')
    return reporters


def produce(board,state,past,groups,*,fake_policy=('noncontradictory','uniform')):
    reporters=require_groups(board,state,past,groups)
    if not reporters:return (PublicationPattern((),groups,(),(),1,1,GeneratedPublication((),F(1),state)),)
    candidates,fake=primitive_laws(board,state,past,reporters,fake_policy)
    first=reporters[0];cats={}
    for row in candidates[first]:
        r=row[0];block=next(g for g in groups if r.target in g)
        key=('peer' if block==reporters else block,r.color)
        cats.setdefault(key,set()).add(r.target)
    for (block,color),targets in cats.items():
        if targets!=(set(reporters)-{first} if block=='peer' else set(block)):
            raise Pending('publication_primitive_support_not_constant_inside_group')
    if len(reporters)==2:
        mapping=list(range(1,board.player_count+1));a,b=reporters;mapping[a-1],mapping[b-1]=b,a
        moved={tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in row)) for row in candidates[a]}
        weighted={tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in row)):q for row,q in fake[a].items()}
        if moved!=candidates[b] or weighted!=fake[b]:raise Pending('publication_reporter_primitive_laws_not_equivariant')
    result=[];ordered=tuple(sorted(cats,key=repr))
    for categories in combinations_with_replacement(ordered,len(reporters)):
        shared=len(reporters)==2 and categories[0][0]==categories[1][0] and categories[0][0]!='peer'
        shapes=(False,True) if shared and len(categories[0][0])>1 else (False,)
        for distinct in shapes:
            rows=[];endpoint_map={}
            for i,(p,(block,color)) in enumerate(zip(reporters,categories)):
                target=next(q for q in reporters if q!=p) if block=='peer' else block[1 if i and distinct else 0]
                template=next(row[0] for row in candidates[p] if row[0].target==target and row[0].color==color)
                rows.append(template)
                if block!='peer' and target not in endpoint_map.setdefault(block,[]):endpoint_map[block].append(target)
            reports=tuple(rows);entries=[]
            for h in state.hypotheses:
                actual_truth=true_reports(h,past,board.alive,board.claims,board.day)
                expected_truth=tuple(r for r in reports if h.roles[2]&(1<<(r.player-1)))
                if actual_truth!=expected_truth:continue
                q=F(1)
                for r in reports:
                    if not h.roles[2]&(1<<(r.player-1)):q*=fake[r.player].get((r,),F())
                if q:entries.append(replace(h,mass=h.mass*q))
            # An impossible public template has exactly zero Q, unlike a
            # positive-Q/zero-P candidate; no invented completion is used.
            if not entries:continue
            one=sum((h.mass for h in entries),F())
            factor=2 if len(reporters)==2 and categories[0]!=categories[1] else 1
            endpoints=tuple((g,tuple(points)) for g,points in endpoint_map.items())
            multiplicity=factor*prod(perm(len(g),len(points)) for g,points in endpoints)
            branch=GeneratedPublication(reports,one,replace(state,hypotheses=normalize(tuple(entries))))
            result.append(PublicationPattern(reporters,groups,categories,endpoints,factor,multiplicity,branch))
    if sum((p.branch.probability*p.multiplicity for p in result),F())!=1:
        raise Pending('publication_pattern_mass_not_complete')
    return tuple(result)


def mappings(pattern,players):
    selections=[tuple(permutations(g,len(points))) for g,points in pattern.endpoints]
    for flip in range(pattern.reporter_factor):
        for selected in product(*selections):
            mapping=list(range(1,players+1))
            if flip:
                a,b=pattern.reporters;mapping[a-1],mapping[b-1]=b,a
            for (group,points),images in zip(pattern.endpoints,selected):
                assigned=dict(zip(points,images));remaining=iter(p for p in group if p not in images)
                for p in group:mapping[p-1]=assigned[p] if p in assigned else next(remaining)
            yield tuple(mapping)


def restore(patterns,players):
    for pattern in patterns:
        for mapping in mappings(pattern,players):
            rows=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in pattern.branch.reports))
            yield GeneratedPublication(rows,pattern.branch.probability,move_law(pattern.branch.state,mapping))


class StructuralPublicationKernel(InformationSetForecast):
    def bind(self,prefix):
        from .cut_out_first_cycle_coverage import check
        check(prefix)
        tracker=InheritedGroupRegistry.__new__(InheritedGroupRegistry)
        tracker.contexts={};tracker.by_board={};tracker.stats=Counter()
        source=prefix.source
        tracker.install(InheritedGroups(source.public,source.public_state,source.past,prefix.groups,event='owned-first-cycle'))
        self.publication_groups=tracker
        self.publication_owner=(prefix.registry,prefix.witness,prefix.registry.data)
        self.pattern_counts={}
        return self
    def valid_owner(self):
        from .cut_out_user_seven_source import require_bound
        if not hasattr(self,'publication_owner'):raise Pending('publication_bound_owner_required')
        r,w,data=self.publication_owner
        if r.data is not data:raise Pending('publication_owner_changed')
        require_bound(r,w)
        if self.rules!=r.engine.baseline.rules or self.strategy!=r.engine.baseline.strategy:
            raise Pending('publication_bound_configuration_changed')
    def morning(self,b,s,past):
        self.valid_owner()
        return super().morning(b,s,past)
    def publications(self,b,s,past):
        self.valid_owner()
        return super().publications(b,s,past)
    def record_group_publication(self,b,s,past,child,state,history,kind):
        self.valid_owner()
        self.publication_groups.publication(b,s,past,child,state,history,kind)
    def generate_publications(self,b,s,past):
        self.valid_owner()
        if self.strategy.disclosure_for('seer')!='all':raise Pending('publication_saved_disclosure_required')
        context=self.publication_groups.require(b,s,past)
        patterns=produce(b,s,past,context.groups,fake_policy=self.strategy.fake_seer_policy)
        self.pattern_counts[b,s,past]=(len(patterns),sum(p.multiplicity for p in patterns))
        return public_report_branches(b,past,restore(patterns,b.player_count))