import unittest
from types import SimpleNamespace
from werewolf.exact import PublicEvent,MediumReport
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import PersonalInformation,GuardInformation,GuardSelection,WolfObserver,information_positions
from werewolf.seer_intervention import SeerObserver
from werewolf.group_partition import _frame_groups,_public_groups


def fix(groups,positions):
    fixed=set(positions);out=[]
    for group in groups:
        out.extend((p,) for p in group if p in fixed)
        rest=tuple(p for p in group if p not in fixed)
        if rest:out.append(rest)
    return tuple(out)


def public(groups,b,past):
    records=[(r.player,('seer',r.acquired_day,r.published_day,'day',r.target,r.color)) for r in past]
    records.extend((r.reporter,('medium',r.day,r.day,'day',r.target,r.color)) for r in b.reports)
    records.extend((p,('opportunity',d,d,'day',t,None)) for d,p,t in b.medium_opportunities)
    records.extend((p,('resolved',d,d,'day',t,None)) for d,p,t in b.report_resolved)
    out=[]
    for group in fix(groups,{r[4] for _,r in records}):
        split={}
        for p in group:split.setdefault(tuple(sorted((r for actor,r in records if actor==p),key=repr)),[]).append(p)
        out.extend(tuple(v) for v in split.values())
    return tuple(out)


def frame(groups,b,past,observer=None,target=None):
    if observer is not None and type(observer) not in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection,WolfObserver):return ()
    fixed={e.target for e in b.history}|(set(range(1,b.player_count+1))-set(b.alive))
    if target is not None:fixed.add(target)
    if observer is not None:fixed.update(information_positions(observer,b.player_count))
    return fix(public(groups,b,past),fixed)


def partitions(xs):
    if not xs:yield ();return
    for groups in partitions(xs[1:]):
        yield ((xs[0],),)+groups
        for i,g in enumerate(groups):yield groups[:i]+((xs[0],)+g,)+groups[i+1:]


class PartitionReferenceTests(unittest.TestCase):
    def test_exhaustive_small_partitions_match_old_refinement(self):
        base=SimpleNamespace(player_count=5,alive=(1,2,3,4,5),history=(),reports=(),medium_opportunities=(),report_resolved=())
        boards=[base,SimpleNamespace(**{**vars(base),'alive':(2,3,4,5),'history':(PublicEvent(1,'day',1),)}),SimpleNamespace(**{**vars(base),'reports':(MediumReport(2,1,5,'white'),),'medium_opportunities':((2,2,5),),'report_resolved':((2,3,5),)})]
        pasts=[(),(SeerReport(1,2,1,5,'white'),),(SeerReport(1,2,1,5,'white'),SeerReport(1,3,2,5,'black'))]
        observers=[None,PersonalInformation(1,'seer'),GuardInformation(2),GuardSelection(2,(),1,3),SeerObserver(3,(),2,1),WolfObserver(3),WolfObserver(5),object()]
        for groups in partitions((1,2,3,4,5)):
            for order in (groups,tuple(reversed(groups))):
                for b in boards:
                    for past in pasts:
                        self.assertEqual(_public_groups(order,b,past),public(order,b,past))
                        for observer in observers:
                            for target in (None,1,4):self.assertEqual(_frame_groups(order,b,past,observer,target=target),frame(order,b,past,observer,target))

    def test_list_and_generator_compatibility_preserve_canonical_output(self):
        b=SimpleNamespace(player_count=3,alive=(1,2,3),history=(),reports=(),medium_opportunities=(),report_resolved=())
        for groups in ([[1],[2],[3]],[(1,),(2,),(3,)]):
            self.assertEqual(_public_groups(groups,b,()),((1,),(2,),(3,)))
            self.assertEqual(_frame_groups(groups,b,()),((1,),(2,),(3,)))
        self.assertEqual(_public_groups(iter(((1,),(2,))),b,()),((1,),(2,)))
