import json
from pathlib import Path
from dataclasses import asdict
from tests.test_board_future import game
from werewolf.exact import Rules,Strategy
from .extension_cases import prepare_game
from .measure_future_reuse import run
from .original_reference import OriginalForecastAdapter
from .general_reuse import GeneralReuseForecast

def main():
    first=game(players=7,wolves=2,mediums=2,seers=1,claims=['seer','medium','medium']+['latent']*4,rules=asdict(Rules(initial_seer='none')),policy=asdict(Strategy()),claim_policy={'medium':'none','seer':'none'},seer_mode='information-fixed-v1',seer_options={'initial_rule':'none','likelihood':'compatibility'},seer_inputs=[])
    observed=json.loads(Path('tests/fixtures/board_saved_seven_observed.json').read_text(encoding='utf-8'))
    rows=[]
    for name,g in(('saved-mixed-seven',first),('saved-observed-seven',observed)):
        prepared=prepare_game(g)
        original=run(prepared=prepared,engine_class=OriginalForecastAdapter,max_seconds=60,max_work=4000000)
        shared=run(prepared=prepared,engine_class=GeneralReuseForecast,enabled=True,compact_keys=True,fast_parts=True,max_seconds=60,max_work=4000000)
        equal=original.get('complete')and shared.get('complete')and(original['value'],original['table'])==(shared['value'],shared['table'])
        rows.append(dict(case=name,reference='corrected semantics; all additional optimization flags OFF; inherited original numerical methods',original=original,shared=shared,equal=equal))
        Path('benchmarks/player_match_groups/saved-corpse-comparisons.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(dict(case=name,equal=equal,original={k:original.get(k)for k in('value','seconds','complete','reason')},shared={k:shared.get(k)for k in('value','seconds','complete','reason')})),flush=True)
if __name__=='__main__':main()
