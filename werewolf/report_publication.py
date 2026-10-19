"""Acquisition day and public Board ownership are separate."""
from dataclasses import replace
from .exact import condition_reports

def publication_slot(g,kind,row):
    key=f"{kind}:{row['day']}:{row['reporter']}"+(f":{row['target']}" if kind=='medium' else '')
    return g.get('public_log',{}).get('report_publications',{}).get(key,{}).get('slot',2*(row['day']-1))

def condition_published_medium(board,reports,history):
    # A latent true medium may manually disclose an earlier result. This only
    # conditions observed reports; future medium report generation is unchanged.
    extra=[]
    existing={(r.day,r.reporter,r.target) for r in board.reports}
    for r in reports:
        index=2*r.day-4
        if (r.day,r.reporter,r.target) in existing:
            extra.append((r.day,r.reporter,r.target));continue
        if index<0 or index>=len(history) or history[index]['target']!=r.target or r.reporter not in board.alive or (board.claims[r.reporter-1]!='medium' and (r.day,r.reporter,r.target) not in board.medium_opportunities):raise ValueError('霊能の取得日・公開者・公開Boardを確認してください。')
        extra.append((r.day,r.reporter,r.target))
    with_opportunities=replace(board,medium_opportunities=tuple(sorted(set(board.medium_opportunities)|set(extra))))
    return condition_reports(with_opportunities,tuple(reports))


def observe_public_reports(source,seer_reports,medium_reports,rules):
    """Current-morning hand observations; no sampled fake-choice likelihood."""
    from .seer_acquisition import SeerReport,publication_support,normalize
    from .exact import MediumReport,condition_reports,available_medium_opportunities
    from .seer_manual import condition
    from .belief_projection import restore_public_history_weights
    from .evaluation_branch import ContinuationInputs,physical_board
    from .information_set_forecast import Pending
    b=source.public
    if source.observer is not None or b.phase!='day' or b.day<2:raise ValueError('Current public morning required')
    if type(seer_reports)is not tuple or any(type(r)is not SeerReport for r in seer_reports):raise ValueError('Typed seer reports required')
    if type(medium_reports)is not tuple or any(type(r)is not MediumReport for r in medium_reports):raise ValueError('Typed medium reports required')
    due={p for p in b.alive if b.claims[p-1]=='seer'}
    if {r.player for r in seer_reports}!=due or len(seer_reports)!=len(due):raise Pending('closed_saved_new_seer_report_pending')
    if any(r.acquired_day!=b.day or r.published_day!=b.day or r.target not in source.public_state.rosters[0] for r in seer_reports):raise ValueError('Only current same-morning reports supported')
    opportunities={o for o in available_medium_opportunities(b) if o[0]==b.day and o not in b.report_resolved}
    if {(r.day,r.reporter,r.target) for r in medium_reports}!=opportunities or len(medium_reports)!=len(opportunities):raise Pending('closed_saved_new_medium_report_pending')
    if any(r.player==p.player and r.acquired_day==p.acquired_day for r in seer_reports for p in source.past):raise ValueError('Past report edits require a new snapshot')
    rows=[dict(day=r.acquired_day,reporter=r.player,target=r.target,color=r.color) for r in seer_reports]
    public=condition(b,rows,{'initial_rule':rules.initial_seer,'likelihood':'compatibility'},source.public_state.rosters[0])
    if medium_reports:
        public=condition_reports(public,tuple((*b.reports,*medium_reports)))
    roles={w[:-1] for w in public.worlds}
    kept=tuple(h for h in publication_support(source.private.hypotheses,seer_reports) if h.roles in roles)
    mass=sum((h.mass for h in kept),0)
    if not mass:raise Pending('observed_report_physical_zero_support')
    own=replace(source.private,hypotheses=normalize(kept))
    try:law=restore_public_history_weights(own,public)
    except ValueError as error:raise Pending('observed_report_public_history_zero_support') from error
    return mass,ContinuationInputs(public,law,tuple(sorted((*source.past,*seer_reports))),own,None,physical_board(public,own,source.physical))
