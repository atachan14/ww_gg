import unittest
from benchmarks.player_match_groups.cut_out_seven_publication_fixture import audit

class SevenPublicationTests(unittest.TestCase):
    def test_derived_count_changes_from_deceased_result_with_fixed_event_groups(self):
        result=audit()
        self.assertEqual([c['wolf_count'] for c in result['cases']],[1,2])
        self.assertEqual(result['morning_vectors'],18)
        self.assertEqual(len(result['rejected']),6)
        self.assertEqual(result['recursive_forecasts'],0)

    def test_publication_never_exchanges_players_or_rebuilds_initial_prior(self):
        from unittest.mock import patch
        from contextlib import ExitStack
        from benchmarks.player_match_groups.cut_out_inherited_groups import InheritedGroupRegistry
        original=InheritedGroupRegistry.publication
        calls=[]
        def guarded(registry,*args,**kwargs):
            with ExitStack() as stack:
                for target in (
                    'benchmarks.player_match_groups.cut_out_day_night.moved_law',
                    'benchmarks.player_match_groups.cut_out_seven_publication_fixture.moved_law',
                    'werewolf.exact.initial_board',
                    'werewolf.exact.combinations',
                    'benchmarks.player_match_groups.constructive_cut_out.ConstructiveCutOutGroups.__init__',
                ):
                    stack.enter_context(patch(target,side_effect=AssertionError('publication called '+target)))
                result=original(registry,*args,**kwargs)
                calls.append(result)
                return result
        with patch.object(InheritedGroupRegistry,'publication',guarded):
            result=audit()
        self.assertGreater(len(calls),18)
        self.assertEqual(result['group_law_swaps'],37)
