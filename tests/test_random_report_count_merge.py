import unittest
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,random_report_outcomes,PublicEvent


class RandomReportCountMergeTests(unittest.TestCase):
    def test_same_public_vector_merges_single_and_mixed_live_wolf_counts(self):
        b=replace_worlds(initial_board(8,2,1),((129,2,0,0,F(1,2)),(3,4,0,0,F(1,2))),
                         alive=(1,2,3,4,5,6),wolf_count=None,day=2,
                         claims=('latent','medium')+('latent',)*6,
                         history=(PublicEvent(1,'day',8),PublicEvent(1,'night',7)),
                         medium_opportunities=((2,2,8),))
        outcomes=random_report_outcomes(b)
        by_color={o.board.reports[-1].color:o for o in outcomes}
        self.assertEqual(by_color['black'].probability,F(3,4))
        self.assertEqual(by_color['black'].board.wolf_count_distribution,{1:F(2,3),2:F(1,3)})
        self.assertIsNone(by_color['black'].board.wolf_count)
        self.assertEqual(by_color['white'].probability,F(1,4))
        self.assertEqual(by_color['white'].board.wolf_count,2)
        self.assertEqual(sum(o.probability for o in outcomes),1)
