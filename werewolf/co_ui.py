"""Role-specific CO presentation; existing single-CO and report semantics stay intact."""
from .exact import available_medium_opportunities

CO_LABELS = dict(latent="潜伏", villager="市民", medium="霊能", seer="占い師", hunter="狩人", wolf="狼")
CO_RENDERERS = {"medium":"co_roles/medium.html", "seer":"co_roles/unavailable.html", "hunter":"co_roles/hunter.html", "villager":"co_roles/no_ability.html", "wolf":"co_roles/no_ability.html"}


def medium_timeline(board, player, finished=False):
    available = {(day, target) for day, reporter, target in available_medium_opportunities(board) if reporter == player}
    opportunities = {day:target for day, reporter, target in board.medium_opportunities if reporter == player}
    reports = {(r.day, r.target):r.color for r in board.reports if r.reporter == player}
    executions = {event.day+1:event.target for event in board.history if event.phase == "day"}
    pending_day = board.day + int(not finished and board.phase == "night" and player in board.alive and board.day+1 in opportunities)
    entries = []
    for day in range(1, pending_day+1):
        target = opportunities.get(day, executions.get(day))
        editable = (day, target) in available and not finished
        color = reports.get((day, target), "")
        state = "result" if color else "input" if editable else "next_day" if day > board.day else "none" if target is None else "unavailable"
        entries.append(dict(day=day, target=target, color=color, editable=editable, state=state))
    return entries
