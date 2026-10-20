"""Build an isolated read-only visual sample using existing engine/API branches."""
import json,sys
from pathlib import Path
from fractions import Fraction
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app import create_app
app=create_app({'TESTING':True,'SECRET_KEY':'isolated-compact-comparison','GAME_TREE_PREVIEW':True})
client=app.test_client();client.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max'})
queue=['0'];nodes={};edges=[]
while queue:
    key=queue.pop(0)
    if key in nodes:continue
    response=client.get('/game-tree',query_string={'node':key,'expand':'1'})
    if response.status_code!=200:raise RuntimeError(response.json)
    node=response.json;nodes[key]={k:node[k] for k in ('node','day','phase','alive','winner','village_win','history')}
    for action in node['actions'] or []:
        if not action['selected']:continue
        for branch in action['branches']:
            mass=Fraction(action['policy_probability'])*Fraction(branch['probability'])
            edges.append(dict(source=key,target=branch['node'],probability=str(mass),conditional_probability=branch['probability'],policy_probability=action['policy_probability'],multiplicity=action['multiplicity'],action='処刑' if node['phase']=='day' else '襲撃',members=branch['variants']))
            queue.append(branch['node'])
assert nodes['0']['village_win']=='7/15'
for node in nodes.values():
    outgoing=[e for e in edges if e['source']==node['node']]
    if outgoing:assert sum(Fraction(e['probability']) for e in outgoing)==1
sample=dict(fixture='市民3・占い1・狼1 · 全潜伏 · 昼夜MAX',nodes=list(nodes.values()),edges=edges)
p=Path(__file__).parent
(p/'sample.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
html=(p/'comparison.template.html').read_text(encoding='utf-8').replace('SAMPLE_JSON',json.dumps(sample,ensure_ascii=False).replace('</','<\\/'))
(p/'index.html').write_text(html,encoding='utf-8')
print(json.dumps(dict(nodes=len(nodes),edges=len(edges),root=nodes['0']['village_win'])))
