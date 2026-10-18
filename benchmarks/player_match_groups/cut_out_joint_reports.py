"""Two surviving reports: public endpoint-pattern orbits before vector expansion."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from itertools import combinations_with_replacement,permutations
from math import perm
from .cut_out_live_medium_reports import prepublication
from .cut_out_joint_night_prototype import move_law,move_board
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.morning_publications import plausible_fake_options,GeneratedPublication,public_report_branches
from werewolf.seer_future_uniform import FuturePending,true_reports
from werewolf.seer_acquisition import SeerReport,normalize
from werewolf.board_future import same_role_board

GROUPS=((1,2),(3,),(4,),(5,6,7))


@dataclass(frozen=True)
class JointReportOrbit:
    categories:tuple
    endpoints:tuple
    reporter_factor:int
    multiplicity:int
    branch:GeneratedPublication


def options(state,past):
    result={}
    for player in (1,2):
        rows=plausible_fake_options(state,(player,),past)
        if isinstance(rows,FuturePending):raise Pending(rows.reason)
        if any(len(reports)!=1 or reports[0].acquired_day!=2 for reports,q in rows):
            raise Pending('joint_report_one_pending_day_required')
        result[player]={reports:q for reports,q in rows}
    return result


def require_source(board,state,past,groups):
    if (board.player_count!=7 or board.initial_hunter_count or board.day!=2 or board.alive!=(1,2,5,6,7)
        or board.reports or board.wolf_count!=2 or tuple(h.target for h in board.history)!=(3,4)
        or groups!=GROUPS or len(state.rosters)!=2 or tuple(p for p in board.alive if board.claims[p-1]=='seer')!=(1,2)):
        raise Pending('joint_report_actual7_execute3_bite4_scope')
    if any(h.roles[2] not in (1,2) or h.roles[1]!=4 or h.roles[0].bit_count()!=2 for h in state.hypotheses):
        raise Pending('joint_report_fixed_CO_role_support_required')
    if any(not h.roles[0]&(2 if h.roles[2]==1 else 1) or (h.roles[0]&sum(1<<(p-1) for p in GROUPS[-1])).bit_count()!=1 for h in state.hypotheses):
        raise Pending('joint_report_one_fake_wolf_and_one_latent_wolf_required')
    seen={(r.player,r.acquired_day) for r in past}
    for h in state.hypotheses:
        scans=tuple(a for a in h.acquisitions if (a.player,a.day) not in seen)
        if len(scans)!=1 or scans[0].day!=2 or not h.roles[2]&(1<<(scans[0].player-1)):
            raise Pending('joint_report_one_true_scan_required')
    for a,b in ((1,2),(5,6),(5,7)):
        mapping=list(range(1,8));mapping[a-1],mapping[b-1]=b,a;mapping=tuple(mapping)
        moved=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in past))
        if move_law(state,mapping)!=state or not same_role_board(move_board(board,state,mapping),board) or moved!=past:
            raise Pending('joint_report_full_public_history_symmetry_required')


def produce(board,state,past,groups=GROUPS):
    """Choose category multisets and equality patterns, not named-vector pairs.

    Legal target/color primitives come from the existing public-support fake
    law. True ownership/results weight each representative's COMPLETE secret
    posterior, including the possibility that either reporter is the true one.
    """
    require_source(board,state,past,groups);law=options(state,past)
    categories={}
    for reports,q in law[1].items():
        row=reports[0];block=next(g for g in groups if row.target in g)
        key=('peer' if block==(1,2) else block,row.color)
        categories.setdefault(key,{})[row.target]=q
    for (block,color),weights in categories.items():
        expected={2} if block=='peer' else set(block)
        if set(weights)!=expected or len(set(weights.values()))!=1:
            raise Pending('joint_report_primitive_group_support_not_uniform')
    mapping=(2,1,3,4,5,6,7)
    swapped={tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in rows)):q for rows,q in law[1].items()}
    if swapped!=law[2]:raise Pending('joint_report_reporter_primitive_law_not_equivariant')
    cats=tuple(sorted(categories,key=repr));result=[]
    for left,right in combinations_with_replacement(cats,2):
        # The only anonymous non-reporter target block has capacity three.
        # Equal/distinct endpoints are structural alternatives, with exact
        # falling-factorial label multiplicity; neither creates named vectors.
        same_block=left[0]==right[0] and left[0]!=(1,2) and left[0]!='peer'
        shapes=(False,True) if same_block and len(left[0])>1 else (False,)
        for distinct in shapes:
            targets=[];endpoints=[]
            for i,(block,color) in enumerate((left,right)):
                target=2-i if block=='peer' else block[1 if i==1 and distinct else 0]
                targets.append(target)
                if target in groups[-1] and target not in endpoints:endpoints.append(target)
            reports=tuple(SeerReport(2,2,p,t,cat[1]) for p,t,cat in zip((1,2),targets,(left,right)))
            entries=[]
            for h in state.hypotheses:
                true_player=1 if h.roles[2]==1 else 2;fake_player=3-true_player
                truth=true_reports(h,past,board.alive,board.claims,2)
                if truth!=(reports[true_player-1],):continue
                fake=(reports[fake_player-1],)
                q=law[fake_player].get(fake,F())
                if q:entries.append(replace(h,mass=h.mass*q))
            if not entries:raise Pending('joint_report_pattern_has_no_public_support')
            mass=sum((h.mass for h in entries),F())
            factor=2 if left!=right else 1
            multiplicity=factor*perm(len(groups[-1]),len(endpoints))
            branch=GeneratedPublication(reports,mass,replace(state,hypotheses=normalize(tuple(entries))))
            result.append(JointReportOrbit((left,right),tuple(endpoints),factor,multiplicity,branch))
    if sum((o.branch.probability*o.multiplicity for o in result),F())!=1:
        raise Pending('joint_report_pattern_mass_incomplete')
    return tuple(result)


def mappings(orbit):
    for flip in range(orbit.reporter_factor):
        for images in permutations(GROUPS[-1],len(orbit.endpoints)):
            mapping=list(range(1,8))
            if flip:mapping[0],mapping[1]=2,1
            assigned=dict(zip(orbit.endpoints,images));remaining=iter(p for p in GROUPS[-1] if p not in images)
            for player in GROUPS[-1]:mapping[player-1]=assigned[player] if player in assigned else next(remaining)
            yield tuple(mapping)


def restore(orbits):
    """Output-only named restoration, no solver or report-law calls."""
    for orbit in orbits:
        for mapping in mappings(orbit):
            reports=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in orbit.branch.reports))
            yield GeneratedPublication(reports,orbit.branch.probability,move_law(orbit.branch.state,mapping))


class JointPublicationKernel(InformationSetForecast):
    def generate_publications(self,b,s,past):
        if b.day==2 and tuple(h.target for h in b.history)==(3,4):
            if tuple(self.strategy.fake_seer_policy)!=('noncontradictory','uniform') or self.strategy.disclosure_for('seer')!='all':
                raise Pending('joint_report_configured_policy_scope')
            return public_report_branches(b,past,restore(produce(b,s,past)))
        return super().generate_publications(b,s,past)


def audit_distribution():
    from time import perf_counter
    start=perf_counter();e,source,chance=prepublication(executed=3)
    orbits=produce(source.public,source.public_state,source.past)
    generated=tuple(public_report_branches(source.public,source.past,restore(orbits)))
    old=e.morning(source.public,source.public_state,source.past)
    key=lambda rows:{(b,p):(q,s) for q,b,s,p in rows}
    assert len(generated)==len(key(generated))==64 and len(orbits)==13
    assert key(generated)==key(old)
    own=lambda rows:{(b,p):(q,s,private) for q,b,s,p,private in rows}
    variants={}
    for name,predicate in (('public',lambda h:True),('roster17',lambda h:h.roles[0]==17),('private_scan5white',lambda h:h.roles[0]==33 and any(a.player==2 and a.day==2 and a.target==5 and a.color=='white' for a in h.acquisitions))):
        private=replace(source.private,hypotheses=normalize(tuple(h for h in source.private.hypotheses if predicate(h))))
        actual=e.push(source.public_state,private,generated);expected=e.push(source.public_state,private,old)
        assert own(actual)==own(expected)
        variants[name]=dict(physical_outputs=len(actual),retained_public_outputs=len(generated),zero_P=64-len(actual))
    assert chance==F(1,4)
    return dict(status='verified',representatives=len(orbits),literal_public_vectors=len(generated),
        primitive_true_fake_pairs=30*8,multiplicities=[o.multiplicity for o in orbits],
        complete_public_private_history_equal=True,variants=variants,total_comparison_seconds=perf_counter()-start)

def make_case(vector=((5,'black'),(5,'black')),*,private='public'):
    from .cut_out_live_medium_forecast import issue_publication_receipt
    from .cut_out_joint_night_forecast import point_fix,physical_board
    from werewolf.board_future import condition_recipe,publication_key
    if private not in ('public','roster17','private_scan5white') or type(vector)is not tuple or len(vector)!=2:
        raise Pending('joint_report_explicit_vector_private_scope')
    for player,row in zip((1,2),vector):
        if (type(row)is not tuple or len(row)!=2 or type(row[0])is not int or
            not 1<=row[0]<=7 or row[0]==player or row[1] not in ('white','black')):
            raise Pending('joint_report_illegal_report_input')
    e,before,_,r,w,request=prepublication(executed=3,kernel_class=JointPublicationKernel,receipt=True)
    if point_fix(GROUPS,3,4)!=point_fix(w.contexts[-1].groups,3,4):
        raise Pending('joint_report_initial_group_receipt_changed')
    if private!='public':
        predicate=(lambda h:h.roles[0]==17) if private=='roster17' else (lambda h:h.roles[0]==33 and any(a.player==2 and a.day==2 and a.target==5 and a.color=='white' for a in h.acquisitions))
        own=replace(before.private,hypotheses=normalize(tuple(h for h in before.private.hypotheses if predicate(h))))
        target=replace(before,private=own,physical=physical_board(before.public,own,before.physical))
        recipe=condition_recipe(before,target)
        if recipe is None:raise Pending('joint_report_private_recipe_unproved')
        request=request.child(recipe,None);before=request.roles()
    rows=e.morning(before.public,before.public_state,before.past)
    wanted=tuple(SeerReport(2,2,p,t,c) for p,(t,c) in zip((1,2),vector))
    selected=[row for row in rows if row[3][len(before.past):]==wanted]
    if len(selected)!=1:raise Pending('joint_report_vector_not_publicly_supported')
    q,b,s,past=selected[0]
    fixed={t for t,c in vector}
    if vector[0]!=vector[1]:fixed.update((1,2))
    groups=point_fix(GROUPS,*sorted(fixed))
    return issue_publication_receipt(r,w,before,request,e,publication_key(b,past),groups,require_equal=private=='public')