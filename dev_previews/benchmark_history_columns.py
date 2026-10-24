"""Public manual-history column metadata; component and full-response timings."""
import hashlib,json,statistics,time
from unittest.mock import patch
from tests.test_manual_public_input import ManualPublicInputTests
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree

doc=NavigationDocument(ManualPublicInputTests().root().data)
for _ in range(30):doc.game.public_input(('latent',)*5,())
# A sibling history must not be added to the depth of the original path.
for _ in range(10):doc.game.back()
for _ in range(5):doc.game.public_input(('latent',)*5,())
v=NavigationTree(doc);v.read(expand=True,compact=True)
parts=[];reads=[]
with patch.object(doc.game.history,'state',wraps=doc.game.history.state) as states:
 expected=v.phase_updates();calls=states.call_count
for _ in range(9):
 start=time.perf_counter();assert v.phase_updates()==expected;parts.append(time.perf_counter()-start)
for _ in range(5):
 start=time.perf_counter();out=v.read(expand=True,compact=True);reads.append(time.perf_counter()-start)
blob=json.dumps(out,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
print(json.dumps(dict(history=len(doc.game.history.export()),phase_updates=expected,metadata_median_ms=round(statistics.median(parts)*1000,3),metadata_state_reads=calls,response_median_ms=round(statistics.median(reads)*1000,3),response_bytes=len(blob),response_sha=hashlib.sha256(blob).hexdigest(),value=out['village_win'])))
