"""Manual observed prior -> future fixed-CO continuation; never alter hand likelihood."""
from itertools import product
from fractions import Fraction as F
from .seer_acquisition import Hypothesis,Acquisition,SeerReport,normalize,from_board
from .seer_future_uniform import TrueScanState,FuturePending
from .seer_future_forecast import forecast
from .calculation_budget import calculation_budget,tick,CalculationBudgetExceeded


def evaluate_game(g,board,rules,strategy,*,max_work=250000):
    if strategy.disclosure_for('seer')=='none':
        # No future acquisition/use/publication: retain already observed evidence.
        from .exact import build_tree,evaluate_tree,legal_targets
        from .seer_future_forecast import Forecast
        try:
            with calculation_budget(max_work):
                root=build_tree(board,rules,strategy);evaluation=evaluate_tree(root,strategy)
                return Forecast(evaluation.board_value(root).village_win,tuple((t,evaluation.action_value(root,t).village_win) for t in legal_targets(board,rules,strategy)))
        except CalculationBudgetExceeded:return FuturePending('future_public_continuation_budget_exceeded')
    tracked=tuple(p for p in board.alive if board.claims[p-1]=='seer')
    initial=g['rules'].get('initial_seer',g['seer_options']['initial_rule'])
    rows={(r['day'],r['reporter']):r for r in g['seer_inputs'] if r['target'] is not None and r['color'] is not None}
    # Current full-disclosure omissions already exclude truth in replay.
    # Never create private true acquisitions to rescue those violations.
    rosters=[]
    for day in range(1,board.day+1):
        dead={e.target for e in board.history if day>1 and (e.day<day-1 or e.day==day-1 and e.phase=='day')}
        rosters.append(tuple(p for p in range(1,g['players']+1) if p not in dead))
    active_only=g.get('public_log',{}).get('version')==2
    entries=[]
    try:
        with calculation_budget(max_work):
            for h in from_board(board):
                tick();owners=tuple(p for p in tracked if h.roles[2]&(1<<(p-1)));variants=[((),F(1))]
                for day,alive in enumerate(rosters,1):
                    choices=[]
                    for p in owners:
                        if day==1 and initial=='none':continue
                        row=rows.get((day,p))
                        if row is not None:
                            choices.append(((Acquisition(day,p,row['target'],row['color']),F(1)),))
                        else:return FuturePending('full_disclosure_truth_not_conditioned')
                    next_variants=[]
                    for records,mass in variants:
                        for selected in product(*choices):
                            tick();q=mass
                            for _,probability in selected:q*=probability
                            next_variants.append((records+tuple(a for a,_ in selected),q))
                    variants=next_variants
                for records,q in variants:entries.append(Hypothesis(h.roles,tuple(sorted(records)),h.mass*q))
            state=TrueScanState(normalize(entries),tuple(rosters),initial,tracked,board.day if active_only else 0)
    except CalculationBudgetExceeded:return FuturePending('observed_prior_private_ledger_budget_exceeded')
    publications=g.get('public_log',{}).get('report_publications',{})
    past=tuple(SeerReport(r['day'],publications.get(f"seer:{r['day']}:{r['reporter']}",{}).get('published_day',r['day']),r['reporter'],r['target'],r['color']) for r in rows.values())
    return forecast(board,state,past,rules,strategy,max_work=max_work)
