import unittest
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.board_flow import BoardData
from werewolf.player_view import ViewScope,ResultFrame,build_public_view,public_view,private_api_rows
from werewolf.exact import Values
from werewolf.by_dawn import HorizonValues
from werewolf.seer_manual import ManualPending
from tests.test_board_flow import game
from tests.fixtures.player_rows_96da610 import build_rows

class DirectPlayerRowTests(unittest.TestCase):
    def inputs(self):
        g=game(seers=1,claims=['seer']+['latent']*4,seer_inputs=[],seer_options={'initial_rule':'random_white'})
        data=BoardData.from_game(g);roles=data.roles();board=roles.board
        return data,roles,board,dict(state=g,event_history=board.history,alive=board.alive,action_values={i:Values(F(1,3),F(2,3))for i in board.alive},by_dawn_values={i:HorizonValues(F(0),F(0))for i in board.alive})
    def test_all_fields_equal_frozen_assembly_manual_pending_and_legal_rows(self):
        data,roles,board,kw=self.inputs()
        for manual in (False,True):
            for pending in (None,ManualPending('reason')):
                frame=ResultFrame(ViewScope.public(data),'pending'if pending else 'complete')
                new=build_public_view(data,roles,board,frame,**kw,manual=manual,probability_pending=pending)
                old=build_rows(role_state=roles,board=board,**kw,manual=manual,role_evidence_pending=pending,seer_pending=pending)
                self.assertEqual([p.to_legacy_row()for p in new.players],old)
    def test_direct_path_does_not_freeze_old_full_row_dicts(self):
        import werewolf.player_view as module
        data,roles,board,kw=self.inputs();frame=ResultFrame(ViewScope.public(data),'complete');original=module.freeze;full=[]
        def track(value):
            if type(value)is dict and module._PUBLIC_REQUIRED<=value.keys():full.append(value)
            return original(value)
        with patch.object(module,'freeze',side_effect=track):
            new=build_public_view(data,roles,board,frame,**kw)
        self.assertEqual(full,[])
        old=build_rows(role_state=roles,board=board,**kw)
        with patch.object(module,'freeze',side_effect=track):public_view(data,old,frame)
        self.assertEqual(len(full),5)
        self.assertEqual([p.to_legacy_row()for p in new.players],old)
    def test_private_boundary_keeps_zero_values_none_and_existing_fields(self):
        marginals=[dict(villager=F(1,2),medium=F(0),seer=F(0),hunter=F(0),wolf=F(1,2))]*3
        actual=private_api_rows(marginals,targets=(2,3),final_values={2:F(0),3:F(1)},dawn_for=lambda p:HorizonValues(F(0),F(0))if p==2 else None)
        self.assertEqual(actual[1]['final'],{'village':'0','wolf':'1'})
        self.assertEqual(actual[2]['final'],{'village':'1','wolf':'0'})
        self.assertEqual(actual[1]['dawn'],{'village':'0','wolf':'0'})
        self.assertIsNone(actual[0]['final']);self.assertEqual(actual[0]['probabilities']['citizen'],'1/2')
        self.assertEqual(set(actual[0]),{'id','probabilities','dawn','final','legal'})

if __name__=='__main__':unittest.main()