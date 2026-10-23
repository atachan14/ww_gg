"""Cookie-isolated smoke of the normal local server; no saved-data mutation."""
import json,urllib.request,urllib.parse,http.cookiejar
base='http://127.0.0.1:18821'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def request(path,values=None,form=False):
 data=None if values is None else (urllib.parse.urlencode(values).encode() if form else json.dumps(values).encode())
 headers={} if data is None or form else {'Content-Type':'application/json'}
 with opener.open(urllib.request.Request(base+path,data=data,headers=headers),timeout=120) as r:
  body=r.read();return json.loads(body) if 'application/json' in r.headers.get('Content-Type','') else body
request('/start',dict(citizens=2,seers=0,mediums=1,hunters=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0),True)
nav=request('/navigation/public-input',dict(revision=0,claims=['medium','latent','latent','latent','latent'],reports=[]))
nav=request('/navigation/advance',dict(revision=nav['revision'],target=3))
night=request('/game-tree?node=h2~0&expand=1')
assert night['evaluation_trace']['ability_program']=='factored-evaluated-flow'
assert night['night_stages']['stats']['medium_results_recorded']>0
assert night['night_stages']['stats']['medium_results_reduced']>0
arrival=next(r for r in night['items'].values() if r.get('day_start') and len(r['alive'])==4 and any(u['label']!='公開なし' for u in r.get('public_updates') or []))
update=next(u['node'] for u in arrival['public_updates'] if u['label']!='公開なし')
for node in (arrival['node'],update):
 nav=request('/navigation');request('/game-tree/current',dict(node=node,snapshot=night['snapshot'],revision=nav['revision']),True)
 nav=request('/navigation');assert nav['board']['day']==2 and len(nav['board']['alive'])==4
 assert request('/main')
ordinary=next(r['node'] for r in night['items'].values() if r.get('day_start') and len(r['alive'])==3 and r.get('public_current') is not False)
nav=request('/navigation');request('/game-tree/current',dict(node=ordinary,snapshot=night['snapshot'],revision=nav['revision']),True)
nav=request('/navigation');assert nav['board']['day']==2 and len(nav['board']['alive'])==3
assert request('/main')
print('normal18821 PASS: evaluated medium/guard records, deathless pre/post-report Current, ordinary-death Current, main HTTP200')
