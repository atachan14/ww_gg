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
