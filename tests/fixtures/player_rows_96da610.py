"""Frozen 96da610 public row assembly; comparison oracle only."""
from werewolf.co_ui import medium_timeline
from werewolf.seer_manual import timeline as seer_timeline

def build_rows(state,role_state,board,event_history,alive,action_values,by_dawn_values,*,finished=False,manual=False,guard_scope_pending=False,role_evidence_pending=None,disclosure_error=None,seer_pending=None):
    deaths = {event.target: f"D{event.day} " + ("処刑" if event.phase == "day" else "襲撃") for event in event_history}
    players = []
    for player in range(1, state["players"] + 1):
        probabilities=role_state.probabilities(player)
        wolf=probabilities['wolf'];medium=probabilities['medium']
        players.append({"medium_probability": medium, "citizen_probability": probabilities['villager'],
                        "extra_probabilities": {r:probabilities[r] for r in ("seer","hunter")},
                        "claim": board.claims[player - 1], "legal": player in action_values or (guard_scope_pending and not finished and board.phase=='day' and player in board.alive),
                        "id": player, "name": f"Player {player}", "status": deaths.get(player, "生存"),
                        "alive": player in alive, "wolf_probability": wolf, "village_probability": 1 - wolf,
                        "action": action_values.get(player), "by_dawn": by_dawn_values.get(player) if player in action_values else None})
    for player in players:
        if manual:
            player['seer_timeline']=seer_timeline(state,board,player['id'],finished)
            player['has_seer_evidence']=any(row['target'] is not None or row['color'] is not None for row in player['seer_timeline'])
        if role_evidence_pending or disclosure_error:
            for key in ('medium_probability','citizen_probability','wolf_probability','village_probability'):player[key]=seer_pending
            player['extra_probabilities']={k:seer_pending for k in player['extra_probabilities']}
        player['medium_timeline'] = medium_timeline(board, player['id'], finished)
        player['co_pending'] = player['claim'] == 'medium' and any(entry['editable'] and not entry['color'] for entry in player['medium_timeline'])
    return players
