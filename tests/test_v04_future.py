import unittest
from fractions import Fraction as F
from dataclasses import replace
from itertools import product
from werewolf.exact import (Board,PublicEvent,MediumReport,report_actions,condition_reports,initial_board,condition_claims,ClaimPolicy,Rules,Strategy,Progress,advance,action_outcomes,legal_targets,replace_worlds,joint_value,Values,aggregate_values,random_report_outcomes)
from werewolf.reports import disclosure,solve_reports

# Independent non-memoized enumeration. Inference for the generated observation
# uses the fixed public fake instruction; current hand input has a separate filter.
def explicit(board,strategy,reveal=False):
    if board.winner:return F(board.winner=='village')
    keys={(r.day,r.reporter,r.target) for r in board.reports}
    ops=tuple(o for o in board.medium_opportunities if reveal and o[0]==board.day and o[1] in board.alive and o not in keys and o not in board.report_resolved)
    if ops:
        fakes=sorted({o[1] for o in ops if board.wolf_probability(o[1])})
        candidates=[];random_groups={}
        for colors in product(('white','black'),repeat=len(fakes)):
            chosen=dict(zip(fakes,colors));groups={}
            for w,m,seer,hunter,q in board.worlds:
                reports=tuple(MediumReport(day,p,t,('black' if w&(1<<(t-1)) else 'white') if m&(1<<(p-1)) else chosen[p]) for day,p,t in ops)
                groups.setdefault(reports,[]).append((w,m,seer,hunter,q))
            if strategy.fake_reports=='random':
                for reports,worlds in groups.items():
                    random_groups.setdefault(reports,[]).extend((*world[:-1],world[-1]/(1<<len(fakes))) for world in worlds)
                continue
            value=F()
            for reports,worlds in groups.items():
                mass=sum(x[-1] for x in worlds)
                child=replace_worlds(board,tuple((*x[:-1],x[-1]/mass) for x in worlds),reports=board.reports+reports,report_resolved=board.report_resolved+ops)
                value+=mass*explicit(child,strategy)
            candidates.append(value)
        if strategy.fake_reports=='random':
            value=F()
            for reports,worlds in random_groups.items():
                mass=sum(x[-1] for x in worlds);combined={}
                for world in worlds:combined[world[:-1]]=combined.get(world[:-1],F())+world[-1]
                child=replace_worlds(board,tuple((*key,q/mass) for key,q in sorted(combined.items())),reports=board.reports+reports,report_resolved=board.report_resolved+ops)
                value+=mass*explicit(child,strategy)
            return value
        return min(candidates)
    candidates=[]
    for target in legal_targets(board,Rules(True),strategy):
        candidates.append(sum((o.probability*explicit(o.board,strategy,board.phase=='night') for o in action_outcomes(board,target,Rules(True),strategy)),F()))
    mode=strategy.day if board.phase=='day' else strategy.night
    return sum(candidates,F())/len(candidates) if mode=='random' else max(candidates) if board.phase=='day' else min(candidates)


def fixture(patterns):
    # r,s,t,u at positions 1..4; extra fixed wolf 5, neutral villagers 6..9.
    worlds=[]
    for pattern in patterns:
        w=(1<<4)|sum(1<<i for i,r in enumerate(pattern) if r=='W')
        m=sum(1<<i for i,r in enumerate(pattern) if r=='M')
        worlds.append((w,m,F(1,len(patterns))))
    return Board(9,(1,2,4,5,6,7,8),None,2,'day',(PublicEvent(1,'day',3),PublicEvent(1,'night',9)),
                 initial_medium_count=patterns[0].count('M'),claims=('medium','medium')+('latent',)*7,
                 role_belief=tuple(worlds),medium_opportunities=((2,1,3),(2,2,3)))


def random_events(board):
    actions=report_actions(board);events={}
    for action in actions:
        for outcome in action.outcomes:
            colors=tuple(r.color for r in outcome.board.reports[-2:])
            event=events.setdefault(colors,{})
            for w,m,q in outcome.board.role_belief:event[w,m]=event.get((w,m),F())+outcome.probability*q/len(actions)
    return events

class FutureReportTests(unittest.TestCase):
    def test_two_true_reports_are_correlated(self):
        b=fixture([('M','M','W','C'),('M','M','C','W')])
        actions=report_actions(b);self.assertEqual(len(actions),1)
        events=random_events(b)
        self.assertEqual({k:sum(v.values()) for k,v in events.items()},{('white','white'):F(1,2),('black','black'):F(1,2)})
    def test_hand_support_and_random_event_probabilities_differ(self):
        b=fixture([('M','W','C','C'),('W','M','C','C')])
        for colors,mass in [(('white','white'),F(1)),(('black','white'),F(1,2)),(('white','black'),F(1,2))]:
            allowed=[q for w,m,q in b.role_belief if all(not m&(1<<i) or color=='white' for i,color in enumerate(colors))]
            self.assertEqual(sum(allowed),mass)
            condition_reports(b,tuple(MediumReport(2,i+1,3,c) for i,c in enumerate(colors)))
        with self.assertRaises(ValueError):condition_reports(b,(MediumReport(2,1,3,'black'),MediumReport(2,2,3,'black')))
        self.assertEqual({k:sum(v.values()) for k,v in random_events(b).items()},{('white','white'):F(1,2),('black','white'):F(1,4),('white','black'):F(1,4)})
    def test_six_world_kernel_recovers_prior_and_approved_posterior(self):
        b=fixture([('M','M','W','C'),('M','M','C','W'),('W','M','M','C'),('W','M','C','M'),('M','W','M','C'),('M','W','C','M')])
        events=random_events(b)
        self.assertEqual({k:sum(v.values()) for k,v in events.items()},{('white','white'):F(1,2),('black','white'):F(1,6),('white','black'):F(1,6),('black','black'):F(1,6)})
        production={tuple(r.color for r in o.board.reports[-2:]):o for o in random_report_outcomes(b)}
        self.assertEqual(production['white','white'].probability,F(1,2))
        expected={key:q/F(1,2) for key,q in events['white','white'].items()}
        self.assertEqual({(w,m):q for w,m,q in production['white','white'].board.role_belief},expected)
        white=events['white','white'];mass=sum(white.values())
        for i,(w,m,q) in enumerate(b.role_belief):
            self.assertEqual(white.get((w,m),F())/mass,F(0) if i==0 else F(1,3) if i==1 else F(1,6))
            self.assertEqual(sum(event.get((w,m),F()) for event in events.values()),q)
        observed=condition_reports(b,(MediumReport(2,1,3,'white'),MediumReport(2,2,3,'white')))
        self.assertEqual(len(observed.role_belief),5)
        self.assertTrue(all(q==F(1,5) for w,m,q in observed.role_belief))
    def test_terminal_mass_stops_before_report_and_no_worldwise_max(self):
        b=condition_claims(initial_board(3,1,1),('medium','latent','latent'),ClaimPolicy())
        outcomes=action_outcomes(b,2,Rules(),Strategy())
        self.assertEqual({o.board.winner:o.probability for o in outcomes},{'village':F(1,2),'wolf':F(1,2)})
        self.assertTrue(all(not report_actions(o.board) for o in outcomes))
        p=advance(Progress(b),2,Rules(),Strategy());self.assertTrue(p.finished);self.assertEqual(p.total_values().village_win,F(1,2))
        # One public maximum of joint values, not a maximum inside each world.
        self.assertEqual(aggregate_values('night',(Values(F(1,2),F(1,2)),Values(F(1,2),F(1,2))),Strategy()).wolf_win,F(1,2))
    def test_exact_solver_matches_independent_unshared_report_tree(self):
        for n,w,m,claims in [(5,1,1,('medium',)+('latent',)*4),(6,2,1,('medium',)+('latent',)*5),(6,1,2,('medium','medium')+('latent',)*4)]:
            b=condition_claims(initial_board(n,w,m),claims,ClaimPolicy(medium='none'))
            for strategy in (Strategy(),Strategy('random','random',False,'random'),Strategy(include_self_bite=True,fake_reports='random')):
                self.assertEqual(joint_value(b,Rules(True),strategy).village_win,explicit(b,strategy))
    def test_extra_ability_free_roles_share_the_same_exact_future_kernel(self):
        b=condition_claims(initial_board(6,1,1,1,1),('medium','seer','hunter')+('latent',)*3,ClaimPolicy(medium='none',seer='none',hunter='none'))
        strategy=Strategy(fake_reports='random')
        self.assertEqual(joint_value(b,Rules(),strategy).village_win,explicit(b,strategy))

    def test_current_blank_not_regenerated_dead_reporter_and_empty_vector(self):
        b=fixture([('M','W','C','C'),('W','M','C','C')])
        self.assertEqual(b.reports,())
        before=joint_value(b,Rules(),Strategy()).village_win
        self.assertEqual(before,joint_value(replace(b,medium_opportunities=()),Rules(),Strategy()).village_win)
        self.assertEqual(b.reports,())
        dead=replace(b,medium_opportunities=((2,9,3),))
        self.assertEqual(report_actions(dead),())
        no_co=replace(b,claims=('latent',)*9,medium_opportunities=())
        self.assertEqual(report_actions(no_co),())

if __name__=='__main__':unittest.main()
