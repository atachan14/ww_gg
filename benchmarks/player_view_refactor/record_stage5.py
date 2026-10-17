"""Record the completed stage-5 regression, never mask known failures."""
import json,re,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'.artifacts/player-match-groups/full-regression.log';raw=p.read_bytes();text=raw.decode('utf8',errors='replace')
m=re.search(r'Ran (\d+) tests in ([0-9.]+)s',text)
if m is None:raise SystemExit('Full regression has not terminated')
failures=[x.strip()for x in re.findall(r'^FAIL: (.+)$',text,re.M)];errors=[x.strip()for x in re.findall(r'^ERROR: (.+)$',text,re.M)]
needle='AssertionError: '+repr(('\u8a08\u7b97\u4e88\u7b97').encode('utf8'))+' not found'
baseline=(ROOT/'.artifacts/browser-backend-qa/full-regression.log').read_text(encoding='utf8',errors='replace')
known=[x for x in failures if x.startswith('test_budget_pending_and_recovery_with_cache (test_seer_manual_general.SeerManualGeneralTests.')and needle in text and needle in baseline]

new=[x for x in failures if x not in known]
seven=json.loads((ROOT/'benchmarks/player_view_refactor/final-seven-short.json').read_text(encoding='utf8'))
result=dict(tested_runtime_commit='68bf2f98b3eb2460fd784f904f517ee234a12644',full_regression=dict(tests=int(m[1]),seconds=float(m[2]),passed=int(m[1])-len(failures)-len(errors),known_failures=known,new_failures=new,errors=errors,clean_pass=not failures and not errors,known_reason_matches_baseline=bool(known),log_sha256=hashlib.sha256(raw).hexdigest()),seven_short=seven,default_matching_groups_enabled=False,nine_win_verified=False,persistent_player_row_schema_added=False,legacy_read_adapters_retained=True)
(ROOT/'benchmarks/player_view_refactor/final-stage5-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps(result['full_regression']))
if new or errors:raise SystemExit('Unexpected regression requires investigation')