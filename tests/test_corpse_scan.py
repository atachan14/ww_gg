import unittest,copy,json
from dataclasses import replace
from fractions import Fraction as F
from werewolf.seer_acquisition import Hypothesis,Acquisition,acquire
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
from werewolf.seer_intervention import scan_intervention_matches

class CorpseScanTests(unittest.TestCase):
    def seed(self):return TrueScanState((Hypothesis((2,0,1,0),(),F(1)),),((1,2,3,4,5),),'none',(1,))
    def test_previously_dead_owner_or_target_is_excluded(self):
        for owner,target in ((True,True),(False,True),(True,False),(False,False)):
            alive=tuple(p for p in range(1,6) if (p!=1 or owner) and (p!=2 or target))
            result=acquire_uniform(self.seed(),alive)
            self.assertEqual(sum(h.mass for h in result.hypotheses),1)
            records=[a for h in result.hypotheses for a in h.acquisitions if a.day==2]
            self.assertEqual({a.target for a in records},set(alive)-{1} if owner else set())
            if owner:self.assertEqual({h.mass for h in result.hypotheses},{F(1,len(alive)-1)})
    def test_obtained_results_survive_later_owner_and_target_death(self):
        seed=self.seed();all_alive=acquire_uniform(seed,(1,2,3,4,5))
        h=next(h for h in all_alive.hypotheses if h.acquisitions[-1].target==2)
        state=replace(all_alive,hypotheses=(replace(h,mass=F(1)),));before=copy.deepcopy(state)
        later=acquire_uniform(state,(3,4,5))
        self.assertEqual(later.hypotheses[0].acquisitions,state.hypotheses[0].acquisitions)
        self.assertTrue(scan_intervention_matches(later.hypotheses[0],later,1,2,2))
        self.assertFalse(scan_intervention_matches(later.hypotheses[0],later,1,2,3))
        self.assertEqual(state,before)
    def test_explicit_instruction_rejects_previously_dead_target(self):
        with self.assertRaises(ValueError):
            acquire(self.seed().hypotheses,2,(1,3,4,5),{1:2},target_players=(1,2,3,4,5))
    def test_initial_white_distribution_is_unchanged(self):
        state=TrueScanState((Hypothesis((2,0,1,0),(),F(1)),),initial_rule='random_white',tracked=(1,))
        result=acquire_uniform(state,(1,2,3,4,5))
        self.assertEqual({(h.acquisitions[0].target,h.acquisitions[0].color,h.mass)for h in result.hypotheses},{(3,'white',F(1,3)),(4,'white',F(1,3)),(5,'white',F(1,3))})

    def test_public_corpse_result_and_later_owner_death_preserve_evidence(self):
        from benchmarks.player_match_groups.extension_cases import fixture,game_of
        from werewolf.board_flow import BoardData
        from werewolf.local_reuse import reuse_scope
        c,g=fixture()
        for target in(4,5):
            g=game_of(c)
            self.assertEqual(c.post('/advance',data={'revision':g['revision'],'target':target,'day':'random','night':'random'}).status_code,303)
        g=game_of(c)
        payload={'claims':g['claims'],'seers':[{'day':day,'reporter':p,'target':3 if day==1 else 5,'color':'white'}for day in(1,2)for p in(1,2)],'mediums':[]}
        invalid=copy.deepcopy(payload)
        for row in invalid['seers']:
            if row['day']==2:row['target']=4
        self.assertEqual(c.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(invalid)}).status_code,400)
        response=c.post('/table-publish',data={'revision':g['revision'],'board_id':g['public_log']['board_id'],'payload':json.dumps(payload)})
        self.assertEqual(response.status_code,200,response.data)
        saved=game_of(c);before=copy.deepcopy(saved);roles=BoardData.from_game(saved).roles()
        bad=copy.deepcopy(payload)
        for row in bad['seers']:
            if row['day']==2:row['color']='black'
        rejected=c.post('/table-publish',data={'revision':saved['revision'],'board_id':saved['public_log']['board_id'],'payload':json.dumps(bad)})
        self.assertEqual(rejected.status_code,400)
        self.assertEqual(game_of(c),before)

        self.assertNotIn(4,roles.board.alive)
        from werewolf.private_adapter import private_slots
        from werewolf.private_view import condition_private
        seer_slots=private_slots(roles.board,1,roles.rules)
        self.assertNotIn(4,next(slot for slot in seer_slots if slot['day']==2)['targets'])
        self.assertNotIn(4,private_slots(roles.board,1,roles.rules,role='hunter')[0]['targets'])
        self.assertNotIn(4,private_slots(roles.board,1,roles.rules,role='wolf')[0]['targets'])
        own=condition_private(roles.board,'seer',[1],[{'day':1,'target':3,'color':'white'},{'day':2,'target':5,'color':'white'}],rules=roles.rules)
        self.assertIn(Acquisition(2,1,5,'white'),own.acquisitions)

        with reuse_scope(False):old=roles.forecast(max_seconds=10)
        with reuse_scope(True):new=roles.forecast(max_seconds=10)
        self.assertEqual(old,new);self.assertEqual(old.village_win,F(1,3))
        self.assertEqual(game_of(c),before)
        # Owner later dies; old Day1 and Day2 public results are not removed.
        self.assertEqual(c.post('/advance',data={'revision':saved['revision'],'target':1,'day':'random','night':'random'}).status_code,303)
        after=game_of(c);self.assertEqual(after['seer_inputs'],saved['seer_inputs'])
        self.assertEqual(c.post('/back',data={'revision':after['revision']}).status_code,303)
        self.assertEqual(game_of(c)['seer_inputs'],saved['seer_inputs'])

    def test_initial_twelve_roles_thirty_six_secrets_and_white_marginals(self):
        from werewolf.exact import initial_board,replace_worlds
        from werewolf.seer_acquisition import from_board
        b=initial_board(5,1,1,1)
        selected=[row for row in b.worlds if row[2]==1];mass=sum(row[-1]for row in selected)
        b=replace_worlds(b,tuple((*row[:-1],row[-1]/mass)for row in selected))
        generated=acquire_uniform(TrueScanState(from_board(b),tracked=(1,)),(1,2,3,4,5))
        self.assertEqual(len({h.roles for h in generated.hypotheses}),12)
        self.assertEqual(len(generated.hypotheses),36)
        for target in(2,3,4,5):
            supported=[h for h in generated.hypotheses if h.acquisitions[0].target==target]
            q=sum(h.mass for h in supported);self.assertEqual(q,F(1,4))
            medium=sum(h.mass for h in supported if h.roles[1]&(1<<(target-1)))/q
            self.assertEqual(medium,F(1,3))
            self.assertEqual(1-medium,F(2,3))

    def test_root_and_fixed_paths_both_exclude_previously_dead_target(self):
        from unittest.mock import patch
        from tests.test_seer_view_forecast import fixture
        from werewolf.exact import Rules,Strategy
        from werewolf.root_secret_flow import RootSecretBranch,root_seer_forecast
        from werewolf.seer_view_forecast import seer_forecast
        b,s=fixture();rules=Rules(initial_seer='none');strategy=Strategy('random','random')
        branch=RootSecretBranch(b,s,b,s,());checks=[]
        def checked(h,state,owner,day,target):
            result=scan_intervention_matches(h,state,owner,day,target)
            if target==5 and len(state.rosters)>=day and owner in state.rosters[day-1]:
                self.assertNotIn(target,state.rosters[day-1])
                self.assertEqual(result,any(a.day==day and a.player==owner and a.target==5 for a in h.acquisitions))
                checks.append(result)
            return result
        with patch('werewolf.root_secret_flow.scan_intervention_matches',checked):
            root=root_seer_forecast(branch,1,(),rules,strategy,max_seconds=10)
        fixed=seer_forecast(b,1,(),rules,strategy,scan_state=s,max_seconds=10)
        self.assertEqual(dict(root),{p:F(1,3)for p in(2,3,4)})
        self.assertEqual(root,fixed)
        self.assertEqual(checks,[])
