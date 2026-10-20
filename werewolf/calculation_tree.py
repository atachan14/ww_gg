"""Local inspection of actual ability-free public evaluations and named Boards.

One immutable Board snapshot owns lazy records. Values use the same existing
exchangeable public evaluator as BoardOverview; named edges use action_outcomes.
This stores no decorative alternate model and never writes saved game evidence.
"""
from dataclasses import asdict
from fractions import Fraction as F
from hashlib import sha256
from threading import RLock
from .exact import Strategy,action_outcomes,legal_targets
from .exchangeable_public import exchangeable_forecast
from .calculation_budget import tick


def supported(data,board):
    g=data.game_data
    return (g.players==5 and g.wolves==1 and not(g.mediums or g.seers or g.hunters)
        and not g.rules.allow_self_bite and all(c=='latent' for c in board.claims)
        and len(board.belief)==len(board.alive)
        and all(mask.bit_count()==1 and mask&board.alive_mask==mask and q==F(1,len(board.alive)) for mask,q in board.belief))


class CalculationTree:
    def __init__(self,data,board,forecast):
        if not supported(data,board):raise ValueError('GameTree currently supports five-player4villager/1wolf, latent CO, no self-bite only')
        self.data=data;self.rules=data.game_data.rules;self.strategy=Strategy(**data.to_game()['policy'])
        if self.strategy.include_self_bite:raise ValueError('Self-bite outside current inspection scope')
        self.snapshot=sha256(data.inputs.encode()).hexdigest()[:20]
        self.nodes={};self.boards={};self.lock=RLock();self.root=self.register(board,forecast)

    def register(self,board,forecast=None):
        if board in self.boards:return self.boards[board]
        tick(0)
        # Same production evaluator, not a separate tree-specific recurrence.
        result=forecast if forecast is not None else exchangeable_forecast(board,self.strategy)
        key=str(len(self.nodes));self.boards[board]=key
        self.nodes[key]={'board':board,'forecast':result,'actions':[] if board.winner else None}
        return key

    def read(self,key,expand=False):
        with self.lock:
            if key not in self.nodes:raise KeyError('Unknown Board')
            record=self.nodes[key];reused=record['actions'] is not None
            b=record['board'];f=record['forecast']
            if expand and record['actions'] is None:
                actions=[];scored=[]
                for target in (() if b.winner else legal_targets(b,self.rules,self.strategy)):
                    outcomes=action_outcomes(b,target,self.rules,self.strategy);rows=[]
                    for outcome in outcomes:
                        tick();existed=outcome.board in self.boards
                        child=self.register(outcome.board)
                        label=('村勝利' if outcome.board.winner=='village' else '狼勝利' if outcome.board.winner=='wolf' else '継続（狼生存）')
                        rows.append({'node':child,'probability':str(outcome.probability),'observation':label,'reused':existed})
                    value=dict(f.action_values)[target]
                    scored.append((target,value));actions.append({'target':target,'label':f'Player{target}を'+('処刑' if b.phase=='day' else '襲撃'),'village_win':str(value),'branches':rows})
                mode=getattr(self.strategy,b.phase)
                best=(max if b.phase=='day' else min)((v for t,v in scored),default=None)
                selected=[t for t,v in scored if mode=='random' or v==best]
                for action in actions:
                    action.update(selected=action['target'] in selected,policy_probability=str(F(1,len(selected))) if action['target'] in selected else '0')
                record['actions']=actions
            return {'snapshot':self.snapshot,'node':key,'day':b.day,'phase':b.phase,'alive':list(b.alive),'winner':b.winner,
                'viewpoint':'公開Q（夜は狼本人の合法手で条件付け）','policy_basis':('狼本人は自分以外の同点候補から選びます。選択確率は公開Qで混合した値です。' if b.phase=='night' else '同点候補はすべて均等採用。手動画面の代表選択とは別です。'),'village_win':str(f.village_win),'wolf_win':str(1-f.village_win),
                'evaluation':'computed','expansion':'computed' if record['actions'] is not None else 'pending','reused':reused,
                'mode':getattr(self.strategy,b.phase),'rules':asdict(self.rules),'policy':asdict(self.strategy),
                'history':[asdict(e) for e in b.history],
                'players':[{'player':p,'alive':p in b.alive,'wolf_probability':str(b.wolf_probability(p))} for p in range(1,b.player_count+1)],
                'actions':record['actions'],'method':'BoardOverviewと同じ終局評価。対称な人数分布の共有を含みます。枝は開いたBoardだけ実際に生成・評価します。'}
