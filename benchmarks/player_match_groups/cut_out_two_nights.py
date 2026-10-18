"""Two-night terminal history readback, without terminal payoff omission."""
from fractions import Fraction as F
from time import perf_counter
from .cut_out_model_a import InitialModelASpec,adapt_six_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules
from werewolf.seer_acquisition import SeerReport
from werewolf.board_future import ActionEvidence,kernel_snapshot,outcome_key,source_key,same_role_board


def spec():
    return InitialModelASpec(6,('seer',)+('latent',)*5,True,mediums=0,
        rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),))


def graph(source=None):return SavedCutOutGraph(adapt_six_model_a(spec() if source is None else source))


def restore_terminals(engine):
    start=perf_counter();rows={};second=dead_after_scan=dead_before_scan=corpse_target=0
    for board,payload,target,outcomes in engine.terminal_records:
        parent=engine.board_sources[source_key(board,payload,engine)]
        for outcome in outcomes:
            key=(board,payload,target,outcome_key(outcome))
            if key in rows:continue
            operation=ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False)
            request=parent.child(operation,(outcome.board.day,outcome.board.phase,outcome.board.alive))
            rebuilt=request.roles()
            direct=engine.action_policy._project_roles(board,payload,outcome,target)
            assert rebuilt.public_state==direct.public_state
            assert rebuilt.private==direct.private and rebuilt.past==direct.past
            assert rebuilt.observer==direct.observer
            assert same_role_board(rebuilt.public,direct.public)
            assert same_role_board(rebuilt.physical,direct.physical)
            assert request.origin is engine.graph.origin
            if board.phase=='night' and board.day==2:
                second+=1
                assert len(rebuilt.public_state.rosters)==3
                assert all(any(a.night==2 and a.target==target for a in h.attacks) for h in rebuilt.private.hypotheses)
            from werewolf.night_knowledge import WolfAttack
            expected_attacks=tuple(WolfAttack(e.day,e.target) for e in rebuilt.public.history if e.phase=='night')
            for law in (rebuilt.public_state,rebuilt.private):
                for h in law.hypotheses:
                    assert h.attacks==expected_attacks
                    for acquisition in h.acquisitions:
                        assert acquisition.player in law.rosters[acquisition.day-1]
                        earlier={a.target for a in h.acquisitions if a.player==acquisition.player and a.day<acquisition.day}
                        if acquisition.day>1:
                            legal={p for p in law.rosters[0] if p!=acquisition.player}
                            unvisited=legal-earlier
                            assert acquisition.target in (unvisited or legal)
                        if acquisition.day==3:
                            dead_after_scan+=acquisition.player==target and board.phase=='night'
                            corpse_target+=acquisition.target not in board.alive
                    for event in rebuilt.public.history:
                        if event.phase=='day':
                            assert not any(a.player==event.target and a.day>event.day for a in h.acquisitions)
                            dead_before_scan+=any(a.player==event.target for a in h.acquisitions)
            for report in rebuilt.past:
                # Generated reports use the morning-survivor roster. Nothing
                # publishes after the second-night terminal observation.
                assert report.published_day<=2
                assert not any(e.target==report.player and (e.day<report.published_day or e.day==report.published_day and e.phase=='day') for e in rebuilt.public.history if e.day<report.published_day)
            rows[key]=(outcome.probability,rebuilt,request)
    return rows,dict(terminal_recipes=len(rows),second_night_terminal_recipes=second,
        killed_after_scan_witnesses=dead_after_scan,executed_owner_old_record_witnesses=dead_before_scan,
        corpse_scan_witnesses=corpse_target,restore_seconds=perf_counter()-start)
