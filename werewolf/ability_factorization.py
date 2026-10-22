"""Disintegrate a retained simultaneous measure; never select a new policy.

An attack orbit requires a single source automorphism fixing the displayed scan
and pushing its complete conditional outcome law to the other target's law.
Equal values, marginals or probabilities alone do not establish an orbit.
"""
from fractions import Fraction as F
from .exact_renaming import renamed_source_signature as signature


def group_attacks(tree,node,scans,attacks):
    source=node.read();identity=tuple(range(1,source.public.player_count+1));original=signature(source,identity)
    def law(attack,ids):
        result={}
        for branch in attack['branches']:
            key=signature(tree.nodes[branch['node']]['node'].read(),ids)
            if key is None:return None
            old=result.get(key,(F(),F()))
            result[key]=(old[0]+F(branch['mass']),old[1]+F(branch['counter']))
        return result
    groups=[]
    for attack in attacks:
        victim=attack['target'];matched=False
        for representative in groups:
            target=representative['target'];mapping=list(identity);mapping[target-1],mapping[victim-1]=victim,target;mapping=tuple(mapping)
            if (original is None or any(mapping[a-1]!=a or mapping[t-1]!=t for a,t in scans)
                or signature(source,mapping)!=original):continue
            left,right=law(representative,identity),law(attack,mapping)
            if left is None or right is None or left!=right:continue
            representative['targets'].append(victim);representative['members'].append(dict(target=victim,transport=list(mapping),branches=attack['branches']))
            for field in ('mass','counter','policy_probability','conditional_probability','probability','reach_probability'):
                if field in attack:representative[field]=str(F(representative[field])+F(attack[field]))
            # Every named image has the same conditional law. Keep its Current
            # recipe as a variant rather than evaluating or inventing a Board.
            for branch in representative['branches']:
                branch.setdefault('variants',[dict(node=branch['node'],target=target,transport=list(identity))])
                key=signature(tree.nodes[branch['node']]['node'].read(),identity)
                branch['variants'].extend(dict(node=b['node'],target=victim,transport=list(mapping)) for b in attack['branches'] if signature(tree.nodes[b['node']]['node'].read(),mapping)==key)
            matched=True;break
        if not matched:
            groups.append({**attack,'targets':[victim],'branches':[dict(b) for b in attack['branches']],
                'members':[dict(target=victim,transport=list(identity),branches=attack['branches'])]})
    for attack in groups:
        targets=attack['targets'];attack['multiplicity']=len(targets)
        suffix=('['+','.join('('+str(p)+')' if p==attack['target'] else str(p) for p in targets)+']\u304b\u3089') if len(targets)>1 else str(attack['target'])+'\u3092'
        attack['label']='\u4eba\u72fc\u304c'+suffix+'\u8972\u6483'
    return groups


def factor(tree,node,choices):
    source=node.read();night=source.public.day;result=[]
    for scan in choices:
        # Supported tree scope contains at most one true seer. A missing scan
        # gets an explicit no-seer result, never a fabricated white/black.
        results={}
        for attack in scan['attacks']:
            for branch in attack['branches']:
                child=tree.nodes[branch['node']]['node'].read()
                colors={tuple(a.color for a in h.acquisitions if a.day==night+1) for h in child.private.hypotheses}
                if len(colors)!=1 or any(len(c)>1 for c in colors):
                    return choices # exact unsplit fallback for unsupported records
                color=next(iter(colors));label={'white':'\u767d','black':'\u9ed2'}.get(color[0],'') if color else '\u5360\u3044\u306a\u3057'
                outcome=results.setdefault(label,dict(mass=F(),counter=F(),attacks={}))
                mass,counter=F(branch['mass']),F(branch['counter']);outcome['mass']+=mass;outcome['counter']+=counter
                row=outcome['attacks'].setdefault(attack['target'],{**attack,'mass':F(),'counter':F(),'branches':[]})
                row['mass']+=mass;row['counter']+=counter;row['branches'].append(dict(branch))
        total_mass=sum(r['mass'] for r in results.values());total_counter=sum(r['counter'] for r in results.values());layers=[]
        for label,outcome in sorted(results.items(),key=lambda pair:({'\u767d':0,'\u9ed2':1}.get(pair[0],2))):
            attacks=[]
            for attack in outcome['attacks'].values():
                mass,counter=attack['mass'],attack['counter'];normalizer=mass or counter
                for b in attack['branches']:b['probability']=str(F(b['mass'] if mass else b['counter'])/normalizer)
                attack.update(mass=str(mass),counter=str(counter),policy_probability=str(mass/outcome['mass'] if outcome['mass'] else F()),
                    probability=str(mass/outcome['mass'] if outcome['mass'] else counter/outcome['counter']),
                    conditional_probability=str(counter/outcome['counter']),reach_probability=str(mass))
                attacks.append(attack)
            layers.append(dict(label=label,probability=str(outcome['mass']/total_mass if total_mass else outcome['counter']/total_counter),
                reach_probability=str(outcome['mass']),conditional_probability=str(outcome['counter']/total_counter),
                private=True,attacks=group_attacks(tree,node,scan['scans'],attacks)))
        result.append({**scan,'results':layers,'attacks':group_attacks(tree,node,scan['scans'],scan['attacks'])})
    return result
