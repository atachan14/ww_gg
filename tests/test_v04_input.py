import unittest
from dataclasses import replace
from fractions import Fraction as F
from app import create_app
from werewolf.exact import (initial_board,condition_claims,group_initial_board,ClaimPolicy,ROLES,world_masks,Rules,Strategy,Progress,advance,condition_reports,MediumReport,available_medium_opportunities,build_tree,evaluate_tree)

NONE=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none')
class ExtraRoleTests(unittest.TestCase):
    def test_complete_counts_joint_mass_and_group_permutation(self):
        b=initial_board(6,1,1,1,1)
        self.assertEqual(len(b.worlds),360)
        self.assertEqual(sum(x[-1] for x in b.worlds),1)
        for role,count in [('villager',2),('medium',1),('seer',1),('hunter',1),('wolf',1)]:
            self.assertEqual(sum(b.role_probability(i,role) for i in b.alive),count)
        claims=('medium','seer','hunter','latent','latent','latent')
        a=group_initial_board(b,claims,NONE)
        swapped=group_initial_board(b,tuple(reversed(claims)),NONE)
        reverse=lambda mask:sum(1<<(5-i) for i in range(6) if mask&(1<<i))
        self.assertEqual({tuple(reverse(mask) for mask in x[:-1]):x[-1] for x in a.worlds},{x[:-1]:x[-1] for x in swapped.worlds})
        self.assertEqual(sum(x[-1] for x in a.worlds),1)
        settings={role:tuple(r for r in ROLES if r!=role) for role in ROLES}
        first=group_initial_board(b,claims,NONE,settings)
        second=group_initial_board(b,claims,NONE,dict(reversed(list(settings.items()))))
        self.assertEqual(first.worlds,second.worlds)
        self.assertEqual({x[:-1]:x[-1] for x in first.worlds},{x[:-1]:x[-1] for x in condition_claims(b,claims,NONE,settings).worlds})
    def test_ability_free_counts_do_not_change_no_co_win_values(self):
        for strategy in (Strategy(),Strategy('random','random'),Strategy(include_self_bite=True)):
            b=initial_board(6,2,1,1,1);old=initial_board(6,2,1)
            def rate(b):return evaluate_tree(build_tree(b,Rules(True),strategy),strategy).board_value(build_tree(b,Rules(True),strategy))
            self.assertEqual(rate(b),rate(old))
            p=advance(Progress(b),1,Rules(True),strategy)
            self.assertEqual(sum(x[-1] for x in p.board.worlds),1)
            self.assertEqual(p.board.initial_seer_count,1)
            self.assertEqual(p.board.initial_hunter_count,1)
    def test_extra_ccos_and_absent_roles(self):
        b=initial_board(6,1,1,1,1);c=('seer','hunter')+('latent',)*4
        a=condition_claims(b,c,ClaimPolicy())
        self.assertEqual(a.role_probability(1,'seer'),1)
        self.assertEqual(a.role_probability(2,'hunter'),1)
        with self.assertRaises(ValueError):condition_claims(initial_board(5),('seer',)+('latent',)*4)
        with self.assertRaises(ValueError):initial_board(5,1,2,2,1)

class MediumInputTests(unittest.TestCase):
    def opening(self,claims,policy=NONE):
        b=condition_claims(initial_board(5,1,1),claims,policy)
        p=advance(Progress(b),2,Rules(),Strategy())
        self.assertEqual(available_medium_opportunities(p.board),())
        return advance(p,3,Rules(),Strategy())
    def test_truth_is_joint_constraint_and_fake_can_lie(self):
        p=self.opening(('medium','latent','latent','latent','latent'))
        b=p.board;self.assertEqual(available_medium_opportunities(b),((2,1,2),))
        r=MediumReport(2,1,2,'black');observed=condition_reports(b,(r,))
        self.assertEqual(observed.wolf_probability(1),1)
        entries=[x for x in b.worlds if not x[1]&1 or x[0]&2]
        mass=sum(x[-1] for x in entries)
        self.assertEqual({x[:-1]:x[-1] for x in observed.worlds},{x[:-1]:x[-1]/mass for x in entries})
        self.assertEqual(sum(x[-1] for x in observed.worlds),1)
        self.assertEqual(condition_reports(observed,(r,)).worlds,observed.worlds)
        self.assertEqual(condition_reports(b,()).worlds,b.worlds)
        self.assertEqual(observed.reports,(r,))
    def test_known_true_conflict_and_no_pre_co_or_dead_report(self):
        p=self.opening(('medium','latent','latent','latent','latent'),ClaimPolicy())
        with self.assertRaises(ValueError):condition_reports(p.board,(MediumReport(2,1,2,'black'),))
        latent=self.opening(('latent',)*5)
        with self.assertRaises(ValueError):condition_reports(latent.board,(MediumReport(2,1,2,'white'),))
        b=condition_claims(initial_board(5,1,1),('medium',)+('latent',)*4,NONE)
        p=advance(Progress(b),2,Rules(),Strategy());p=advance(p,1,Rules(),Strategy())
        self.assertEqual(available_medium_opportunities(p.board),())
    def test_joint_reports_are_not_independent_probabilities(self):
        b=condition_claims(initial_board(7,2,2),('medium','medium')+('latent',)*5,NONE)
        p=advance(Progress(b),3,Rules(),Strategy());p=advance(p,4,Rules(),Strategy())
        reports=(MediumReport(2,1,3,'white'),MediumReport(2,2,3,'black'))
        out=condition_reports(p.board,reports)
        self.assertTrue(all(not (world[1]&1 and world[1]&2) for world in out.worlds))
        self.assertEqual(sum(world[-1] for world in out.worlds),1)

    def test_report_evidence_survives_reporter_death(self):
        b=condition_claims(initial_board(7,2,2),('medium','medium')+('latent',)*5,NONE)
        p=advance(Progress(b),3,Rules(),Strategy());p=advance(p,4,Rules(),Strategy())
        reports=(MediumReport(2,1,3,'white'),MediumReport(2,2,3,'black'))
        observed=condition_reports(p.board,reports)
        p=Progress(observed,p.settled_village,p.settled_wolf,p.last_board,p.last_outcomes)
        p=advance(p,1,Rules(),Strategy())
        self.assertFalse(p.finished)
        self.assertEqual(p.board.reports,reports)
        self.assertEqual(condition_reports(p.board,reports).worlds,p.board.worlds)
        self.assertTrue(all(o[1]!=1 for o in p.board.medium_opportunities if o[0]==3))

class MediumWebTests(unittest.TestCase):
    def setUp(self):
        self.c=create_app({'TESTING':True,'SECRET_KEY':'v04-test'}).test_client()
    def state(self):
        with self.c.session_transaction() as s:return s['game']
    def form(self,**changes):
        s=self.state();data={'revision':str(s['revision']),'day':'max','night':'max'};data.update(changes);return data
    def test_report_snapshot_add_remove_back_and_extra_roles(self):
        self.assertEqual(self.c.post('/start',data={'citizens':'3','mediums':'1','wolves':'1','day':'max','night':'max','cco_medium':'none'}).status_code,303)
        self.c.post('/strategy',data=self.form(co_1='medium'))
        self.c.post('/advance',data=self.form(target='2'))
        self.c.post('/advance',data=self.form(target='3'))
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('name="report_2_1_2"',html)
        self.assertIn('value="" selected>未入力',html)
        self.assertNotIn('reports',self.state())
        history=self.state()['history'][:]
        response=self.c.post('/strategy',data=self.form(report_2_1_2='black'))
        self.assertEqual(response.status_code,303)
        self.assertEqual(self.state()['reports'],[{'day':2,'reporter':1,'target':2,'color':'black'}])
        self.assertEqual(self.state()['history'],history)
        self.c.post('/strategy',data=self.form(report_2_1_2=''))
        self.assertEqual(self.state()['reports'],[])
        before=self.state();self.assertEqual(self.c.post('/strategy',data=self.form(report_2_1_2='invalid')).status_code,400);self.assertEqual(self.state(),before)
        self.c.post('/back',data={'revision':str(self.state()['revision'])})
        self.assertNotIn('name="report_2_1_2"',self.c.get('/main').get_data(as_text=True))
        self.assertEqual(self.c.post('/start',data={'citizens':'2','mediums':'1','seers':'1','hunters':'1','wolves':'1','day':'max','night':'max'}).status_code,303)
        self.assertEqual((self.state()['players'],self.state()['seers'],self.state()['hunters']),(6,1,1))
        html=self.c.get('/main').get_data(as_text=True)
        self.assertIn('占い師（手動のみ）',html);self.assertIn('id="public-log-seed"',html);self.assertIn('"seer"',html);self.assertIn('"hunter"',html)

if __name__=='__main__':unittest.main()
