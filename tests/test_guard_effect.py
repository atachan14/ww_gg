import copy,unittest
from types import SimpleNamespace
from werewolf.guard_effect import GuardIntent,DeathCause,resolve_first_guard,resolve_guard_frame
from werewolf.action_flow import NightFrame


class GuardEffectTests(unittest.TestCase):
    roles=('hunter','villager','wolf','villager')
    alive=(1,2,3,4)

    def test_match_cancels_only_attack(self):
        r=resolve_first_guard(self.roles,self.alive,GuardIntent(1,1,2),2)
        self.assertTrue(r.prevented_attack);self.assertEqual(r.deaths,());self.assertEqual(r.survivors,self.alive)

    def test_mismatch_and_guardian_attacked(self):
        for attack in (1,4):
            with self.subTest(attack=attack):
                r=resolve_first_guard(self.roles,self.alive,GuardIntent(1,1,2),attack)
                self.assertFalse(r.prevented_attack)
                self.assertEqual(r.deaths,(DeathCause(attack,'wolf_attack'),))
                self.assertNotIn(attack,r.survivors)

    def test_other_causes_remain_even_on_guarded_person_and_guardian(self):
        other=(DeathCause(2,'poison'),DeathCause(1,'separate_effect'))
        r=resolve_first_guard(self.roles,self.alive,GuardIntent(1,1,2),2,other)
        self.assertTrue(r.prevented_attack);self.assertEqual(r.deaths,other)
        self.assertEqual(r.survivors,(3,4))
        r=resolve_first_guard(self.roles,self.alive,GuardIntent(1,1,2),4,other)
        self.assertEqual(r.deaths,(DeathCause(4,'wolf_attack'),)+other)

    def test_invalid_and_out_of_scope_inputs(self):
        good=(self.roles,self.alive,GuardIntent(1,1,2),2,())
        changes=((0,('hunter','hunter','wolf','villager')),(0,('hunter','bad','wolf','villager')),
                 (0,('hunter','villager','villager','villager')),(1,(2,3,4)),(1,(1,1,3,4)),
                 (1,(True,2,3,4)),(1,([],2,3,4)),(1,(1,2,3,5)),(1,(1,2,4)),(2,GuardIntent(2,1,2)),
                 (2,GuardIntent(True,1,2)),(2,GuardIntent(1,2,4)),(2,GuardIntent(1,1,1)),
                 (2,GuardIntent(1,1,5)),(3,True),(3,5),(4,[]),
                 (4,(DeathCause(2,'wolf_attack'),)),(4,(DeathCause(5,'poison'),)),
                 (4,(DeathCause(2,''),)))
        for index,value in changes:
            args=list(good);args[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):resolve_first_guard(*args)

    def test_frame_uses_acquired_intent_and_does_not_mutate_input(self):
        board=SimpleNamespace(day=1,phase='night',alive=self.alive)
        frame=NightFrame(board,2,GuardIntent(1,1,4),GuardIntent(1,1,2))
        before=copy.deepcopy((frame,self.roles))
        first=resolve_guard_frame(frame,self.roles)
        self.assertTrue(first.prevented_attack)
        self.assertEqual(resolve_guard_frame(frame,self.roles),first)
        self.assertEqual((frame,self.roles),before)
        with self.assertRaises(ValueError):resolve_guard_frame(NightFrame(SimpleNamespace(day=2,phase='night'),2,None,frame.after),self.roles)
        for invalid in (None,NightFrame(SimpleNamespace(day=True,phase='night'),2,None,frame.after),
                        NightFrame(SimpleNamespace(day=1,phase='night',player_count=5),2,None,frame.after)):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):resolve_guard_frame(invalid,self.roles)
