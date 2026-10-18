"""Minimal reproduction and opt-in closed-disclosure proof; no default change."""
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_model_a import InitialModelASpec,source_game
from werewolf.exact import Rules,ClaimPolicy
from werewolf.seer_acquisition import SeerReport
from werewolf.public_log import migrate,transaction
from werewolf.public_log_changes import upgrade,project_changes,declarations
from werewolf.board_flow import BoardData
from werewolf.board_future import SavedOrigin
from werewolf.root_secret_flow import replay_root_secrets
from werewolf.seer_future_uniform import FuturePending
from werewolf.information_set_forecast import Pending


def minimal_four(*,report=True):
    spec=InitialModelASpec(4,('seer','latent','latent','latent'),True,mediums=0,
        rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),) if report else (),
        claim_policy=ClaimPolicy(villager='none',medium='none',seer='none',hunter='none'))
    game=source_game(spec);game.pop('public_log')
    game['history']=[dict({k:game[k] for k in ('claims','claim_policy','policy','seer_options','result_disclosure_model')},target=2)]
    game['public_log']=upgrade(migrate(game));game=project_changes(game,game['public_log'])
    original=BoardData.from_game(game);active=declarations(game['public_log'])[0]
    changed=transaction(game,original.roles().board,{'mode':'simultaneous','events':[dict(e,action='withdraw',ref=e['id']) for _,e in active.values()]})
    return spec,original,BoardData.from_game(changed)


def examine(spec,data):
    roles=data.roles();board=roles.board
    try:
        SavedOrigin(data,spec.rules,spec.strategy,project_public=False)()
        previous='completed'
    except Pending as error:previous=error.reason
    branch=replay_root_secrets(data.to_game(),board,spec.rules,spec.strategy,
        max_work=1000000,max_seconds=20,_historical_disclosure_proof=True)
    assert not isinstance(branch,FuturePending),branch
    assert branch.public_law.public_roles==tuple(sorted(board.worlds))
    assert sum((h.mass for h in branch.public_law.hypotheses),F())==1
    assert sum((h.mass for h in branch.physical_law.hypotheses),F())==1
    assert not branch.past # No retired concrete report is resurrected.
    return dict(default_result=previous,old_role_oracle_preserved=True,
        wolf_rates={str(p):str(board.wolf_probability(p)) for p in board.alive},
        public_hypotheses=len(branch.public_law.hypotheses),physical_hypotheses=len(branch.physical_law.hypotheses),
        truth1_initial_targets=sorted({a.target for h in branch.public_law.hypotheses for a in h.acquisitions if a.player==1}),
        active_concrete_reports=len(data.to_game()['seer_inputs']),retired_report_contents_used=False),branch
