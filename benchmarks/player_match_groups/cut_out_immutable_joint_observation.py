"""One fixed3000 observation of complete joint values and replay shells."""
import time
START=time.perf_counter()
import os,sys,json,threading
from pathlib import Path
from collections import defaultdict


def census(engine):
    from werewolf.seer_future_uniform import TrueScanState
    refs=[item[0] for item in engine.board_key_hashes.values()]
    laws={id(v):v for v in refs if type(v)is TrueScanState}
    hs={id(h):h for law in laws.values() for h in law.hypotheses}
    records={kind:{id(r):r for h in hs.values() for r in getattr(h,kind)} for kind in ('acquisitions','guards','attacks')}
    ops={id(op):op for req in engine.board_sources.values() for op in req.history}
    snapshots={id(op.engine):op.engine for op in ops.values() if hasattr(op,'engine')}
    def values(items):
        rows=list(items)
        return dict(identity_count=len({id(x) for x in rows}),complete_value_count=len(set(rows)),
                    shallow_object_plus_dict_bytes=sum(sys.getsizeof(x)+sys.getsizeof(vars(x)) for x in {id(v):v for v in rows}.values()))
    by_roles=defaultdict(set)
    for law in laws.values():by_roles[law.public_roles].add(law)
    names=set().union(*(vars(s) for s in snapshots.values()))
    exact_shared_fields=[name for name in names if len({id(vars(s).get(name)) for s in snapshots.values()})==1]
    return dict(laws=values(laws.values()),hypotheses=values(hs.values()),
        hypothesis_tuples=dict(identity_count=len({id(s.hypotheses) for s in laws.values()}),complete_value_count=len({s.hypotheses for s in laws.values()})),
        records={k:values(v.values()) for k,v in records.items()},
        same_role_marginal_but_different_complete_law_groups=sum(len(v)>1 for v in by_roles.values()),
        largest_number_of_distinct_complete_laws_with_one_role_marginal=max(map(len,by_roles.values())),
        proof_snapshot_count=len(snapshots),proof_snapshot_dict_bytes=sum(sys.getsizeof(vars(s)) for s in snapshots.values()),
        proof_snapshot_exact_same_reference_field_count=len(exact_shared_fields),proof_snapshot_exact_same_reference_fields=sorted(exact_shared_fields),
        proof_snapshot_varying_fields=sorted(names-set(exact_shared_fields)),
        memory_scope='shallow object+__dict__ sizes and exact-value counts in identity-hash joint laws and source-recipe snapshots; not whole heap')


def run():
    from .cut_out_compact_terminal import CompactTerminalInitialEngine
    from .cut_out_initial_publications import base,scope,stats
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.board_future import calculation_origin,remember
    from werewolf.calculation_budget import calculation_budget
    class Stop(Exception):pass
    class Probe(CompactTerminalInitialEngine):
        def act(self,*args,**kwargs):
            value=super().act(*args,**kwargs)
            if len(self.scalar_actions)==3000 and not getattr(self,'_board_evidence_snapshot',False):raise Stop()
            return value
    def watch():
        while True:
            if time.perf_counter()-START>9.7 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.025)
    threading.Thread(target=watch,daemon=True).start()
    with calculation_budget(None,max_seconds=8):
        graph,w=base();root=scope(graph,w);engine=Probe(graph,witness=w);engine.capture_terminal=True
        try:
            with calculation_origin(graph.data):remember(engine,graph.root,root);engine.solve(*root,physical=root.physical)
        except Stop:pass
    row=dict(status='fixed3000_observed',stats=stats(engine),peak_before_census_bytes=peak_bytes(),census=census(engine),worker_seconds=time.perf_counter()-START)
    Path('benchmarks/player_match_groups/immutable-joint-observation.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row['census']),flush=True)

if __name__=='__main__':run()
