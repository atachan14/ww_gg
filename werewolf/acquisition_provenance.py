"""Opt-in uniform acquisition lineage and trusted audited-group bindings.

Receipts attest a trusted generator invocation and exact carrier references.
Root audits remain a trusted adapter obligation; the ledger never infers a root
from marginal roles, endpoint metadata or an arbitrary callback. Receipts do not
alter numerical keys or automatically authorize a merge.
Typed owner observations, H0 uniform acquisition/death/report transitions and
uniform wolf information/choice are supported. Unknown observers decline.
Unknown cache identities and replay snapshots retain ordinary results unproved.
"""
from collections import Counter
from dataclasses import dataclass
from weakref import ref,WeakKeyDictionary
from collections.abc import MutableMapping


def _frame(board,payload):
    return (board,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)


def _same_references(left,right):
    return len(left)==len(right) and all(a is b for a,b in zip(left,right))


@dataclass(frozen=True,eq=False)
class UniformAcquisitionReceipt:
    parent:object
    operation:str='unobserved_uniform_acquisition'
    groups:object=None
    observation_mass:object=1


@dataclass(frozen=True,eq=False)
class AuditedGroupReceipt:
    groups:tuple


@dataclass(frozen=True,eq=False)
class TransitionReceipt:
    parent:object
    groups:tuple
    operation:str
    public_mass:object
    private_mass:object
    public_kernel:str
    private_kernel:str


class UniformAcquisitionCache(MutableMapping):
    """Raw-value mapping with an internal per-fill provenance ticket.

    Normal writes/updates have no ticket. A canonical lookup obtains value and
    ticket together, so proof code does not repeat full cache-key equality.
    """
    def __init__(self):self._entries={}
    def __getitem__(self,key):return self._entries[key][0]
    def __setitem__(self,key,value):self._entries[key]=(value,None)
    def __delitem__(self,key):del self._entries[key]
    def __iter__(self):return iter(self._entries)
    def __len__(self):return len(self._entries)
    def _lookup(self,key):return self._entries[key]
    def _store_generated(self,key,value,ticket):self._entries[key]=(value,ticket)
    def copy(self):return dict(self.items())


class AcquisitionLedger:
    def __init__(self,engine):
        self._engine=ref(engine)
        self._configuration=(engine.rules,engine.strategy)
        self._generations={}
        self._issued=WeakKeyDictionary()
        self._roots=WeakKeyDictionary()
        self._transitions=WeakKeyDictionary()
        self._requests=WeakKeyDictionary()
        self._frames={}
        self._deaths={}
        self._public_deaths={}
        self._publications={}
        self._morning_components={}
        self._mornings={}
        self._weighted_reports={}
        self._report_batches={}
        self._canonical_laws={}
        self._canonical_boards={}
        self._cache_tickets={}
        self._observed_generations={}
        self._selections=WeakKeyDictionary()
        self._information_outputs={}
        self._policy_generations={}
        self._observation_masses=WeakKeyDictionary()
        self.stats=Counter()

    def _supported(self):
        e=self._engine()
        if e is None:return False
        rules,strategy=self._configuration
        return (e.rules is rules and e.strategy is strategy
            and not getattr(e,'_board_evidence_snapshot',False)
            and (strategy.day,strategy.night,strategy.fake_reports)==('random',)*3
            and tuple(strategy.seer_position)==('unvisited','uniform'))

    def _record_uniform(self,board,before,after):
        # Called only at the canonical acquire_uniform cache fill. Equivalent
        # but nonidentical cache keys are intentionally not re-proved here.
        if not self._supported():return
        self._generations[id(board),id(before)]=(board,before,after)
        self.stats['generation_records']+=1
        ticket=object();self._cache_tickets[ticket]=(board,before,after)
        if self._canonical_laws.get(id(before)) is before:self._canonical_laws[id(after)]=after
        return ticket

    def _record_cache_equivalence(self,board,before,after,ticket):
        if not self._supported() or self._generation(board,before,after):return
        row=self._cache_tickets.get(ticket)
        if (row is None or row[2] is not after
            or self._canonical_laws.get(id(row[1])) is not row[1]
            or self._canonical_laws.get(id(before)) is not before
            or self._canonical_boards.get(id(row[0])) is not row[0]
            or self._canonical_boards.get(id(board)) is not board):return
        # The canonical cache has already matched the complete numerical key.
        self._generations[id(board),id(before)]=(board,before,after)
        self.stats['trusted_cache_equivalence_links']+=1

    def _generation(self,board,before,after):
        row=self._generations.get((id(board),id(before)))
        return row is not None and _same_references(row,(board,before,after))

    def _bind(self,board,before,after):
        if not self._supported():
            self.stats['configuration_declines']+=1;return None
        if not self._observer_supported(before.observer) or after.observer is not before.observer:
            # A caller predicate is an observation operation with a separate
            # proof obligation, even if it happens to retain every hypothesis.
            self.stats['observer_declines']+=1;return None
        if board.phase!='night' or board.initial_hunter_count:
            self.stats['scope_declines']+=1;return None
        if not (self._generation(board,before.public_state,after.public_state)
                and (self._generation(board,before.private,after.private) or self._observed_generation(board,before.private,after.private,before.observer))):
            self.stats['unknown_generation_declines']+=1;return None
        groups=self.groups_for(before.provenance,board,before)
        if groups is not None:groups=self._fix(groups,self._observer_positions(before.observer))
        inherited=self._groups_record(before.provenance) if groups is not None else None
        owner=None if inherited is None else inherited[2]
        observation=self._observed_generations.get((id(board),id(before.private),id(after.private),id(before.observer)))
        receipt=UniformAcquisitionReceipt(before.provenance,groups=groups,observation_mass=1 if observation is None else observation[4])
        self._observation_masses[receipt]=receipt.observation_mass
        self._issued[receipt]=(_frame(board,before),_frame(board,after),receipt.parent,receipt.operation,groups,owner)
        self.stats['paired_receipts']+=1
        if groups is not None:self.stats['inherited_groups']+=1
        if groups is not None:
            self._remember_frame(receipt,board,after)
            request=self.request_for(before.provenance)
            if request is not None:self._requests[receipt]=ref(request)
        return receipt

    def validates(self,receipt,board,before,after):
        """Fixed-field identity checks; no state hash/equality or parent replay."""
        self.stats['validation_requests']+=1
        if not self._supported() or type(receipt)is not UniformAcquisitionReceipt:return False
        row=self._issued.get(receipt)
        if row is None or receipt.observation_mass is not self._observation_masses.get(receipt):return False
        parent,child,prior,operation,groups,owner=row
        if groups is not None and (owner is None or not self._owner_current(owner)):return False
        return (after.provenance is receipt and before.provenance is prior and receipt.parent is prior and receipt.operation is operation
            and receipt.groups is groups
            and _same_references(parent,_frame(board,before))
            and _same_references(child,_frame(board,after)))

    def _register_audited_root(self,board,payload,groups,owner,*,request=None):
        """Trusted adapter seam AFTER a complete root audit, not an auditor.

        Callers must not expose this internal assertion as an input API.
        owner=(graph, immutable_saved_data) binds later use to the audited game.
        """
        if not self._supported():return None
        if (type(groups)is not tuple or any(type(g)is not tuple or not g or any(type(p)is not int for p in g) for g in groups)
            or tuple(sorted(p for g in groups for p in g))!=tuple(range(1,board.player_count+1))):
            raise ValueError('Audited groups must partition original players')
        graph,data=owner
        if graph.data is not data:raise ValueError('Audited owner changed')
        from .belief_projection import _normalized_immutable_state
        from .exact import Board
        if type(board)is not Board or type(payload.physical)is not Board:raise ValueError('Canonical root Boards required')
        for law in (payload.public_state,payload.private):
            if self._canonical_laws.get(id(law)) is law:continue
            self.stats['root_canonical_hypothesis_visits']+=len(law.hypotheses)
            if not _normalized_immutable_state(law):raise ValueError('Canonical complete root law required')
            self._canonical_laws[id(law)]=law
        self._canonical_boards[id(board)]=board;self._canonical_boards[id(payload.physical)]=payload.physical
        receipt=AuditedGroupReceipt(groups)
        baseline=graph.engine.baseline
        self._roots[receipt]=(_frame(board,payload),groups,(graph,data,graph.engine,graph.root,graph.origin,baseline,baseline.rules,baseline.strategy))
        self.stats['audited_roots']+=1
        self._remember_frame(receipt,board,payload)
        if request is not None:self._attach_request(receipt,request)
        return receipt

    def _groups_record(self,receipt):
        if not self._supported():return None
        if type(receipt)is AuditedGroupReceipt:
            row=self._roots.get(receipt)
            if row is None:return None
            frame,groups,owner=row
            if receipt.groups is not groups or not self._owner_current(owner):return None
            return frame,groups,owner
        if type(receipt)is UniformAcquisitionReceipt:
            row=self._issued.get(receipt)
            if row is None or receipt.observation_mass is not self._observation_masses.get(receipt):return None
            parent,child,prior,operation,groups,owner=row
            # Owner was sealed at issue time. No parent walk, full-state
            # equality or replay is needed at consumption.
            if (owner is None or groups is None or receipt.groups is not groups
                or receipt.parent is not prior or receipt.operation is not operation):return None
            if not self._owner_current(owner):return None
            return child,groups,owner
        if type(receipt)is TransitionReceipt:
            row=self._transitions.get(receipt)
            if row is None:return None
            frame,owner,fields=row
            if not _same_references(tuple(vars(receipt).values()),fields) or not self._owner_current(owner):return None
            return frame,receipt.groups,owner
        return None

    @staticmethod
    def _owner_current(owner):
        from .board_future import active_calculation_data
        graph,data,engine,root,origin,baseline,rules,strategy=owner
        active=active_calculation_data()
        return ((active is None or active is data) and graph.data is data and graph.engine is engine and graph.root is root and graph.origin is origin
            and engine.baseline is baseline and baseline.rules is rules and baseline.strategy is strategy)

    def groups_for(self,receipt,board,payload):
        """Consume only an exact, owned frame; never compare complete laws."""
        row=self._groups_record(receipt)
        if row is None:return None
        frame,groups,owner=row
        if payload.provenance is not receipt or not _same_references(frame,_frame(board,payload)):
            return None
        self.stats['group_consumptions']+=1
        return groups

    def public_groups_for(self,receipt,board,state,past):
        row=self._groups_record(receipt)
        if row is None:return None
        frame,groups,owner=row
        if not _same_references(frame[:3],(board,state,past)):return None
        return groups

    def _remember_frame(self,receipt,board,payload):
        self._frames[tuple(map(id,_frame(board,payload)))]=ref(receipt)

    def receipt_for_frame(self,board,payload):
        token=self._frames.get(tuple(map(id,_frame(board,payload))))
        receipt=None if token is None else token()
        row=self._groups_record(receipt)
        if row is None or not _same_references(row[0],_frame(board,payload)):return None
        self.stats['frame_identity_reuses']+=1
        return receipt

    def _attach_request(self,receipt,request):
        row=self._groups_record(receipt)
        if row is None or request.origin is not row[2][3].origin:return False
        self._requests[receipt]=ref(request)
        return True

    def request_for(self,receipt):
        if self._groups_record(receipt) is None:return None
        entry=self._requests.get(receipt)
        return None if entry is None else entry()

    def owner_for(self,receipt):
        row=self._groups_record(receipt)
        return None if row is None else row[2][0]

    def evidence_parent(self,board,payload):
        from .evaluation_branch import ContinuationInputs
        if self.groups_for(payload.provenance,board,payload) is None:return None
        request=self.request_for(payload.provenance)
        if request is None:return None
        row=self._issued.get(payload.provenance) if type(payload.provenance)is UniformAcquisitionReceipt else None
        frame=row[0] if row is not None else _frame(board,payload)
        b,q,past,p,observer,physical=frame
        return request,ContinuationInputs(b,q,past,p,observer,physical)

    def _mint_transition(self,before,after,groups,operation,q,p,qkernel,pkernel):
        inherited=self._groups_record(before.provenance)
        if inherited is None:return None
        receipt=TransitionReceipt(before.provenance,groups,operation,q,p,qkernel,pkernel)
        self._transitions[receipt]=(_frame(after.public,after),inherited[2],tuple(vars(receipt).values()))
        self._canonical_laws[id(after.public_state)]=after.public_state
        self._canonical_laws[id(after.private)]=after.private
        self._canonical_boards[id(after.public)]=after.public
        self._canonical_boards[id(after.physical)]=after.physical
        self._remember_frame(receipt,after.public,after)
        return receipt

    @staticmethod
    def _fix(groups,positions):
        fixed=set(positions);result=[]
        for group in groups:
            result.extend((p,) for p in group if p in fixed)
            rest=tuple(p for p in group if p not in fixed)
            if rest:result.append(rest)
        return tuple(result)

    def _canonical_death(self):
        from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy
        e=self._engine()
        return (self._supported() and getattr(e.public_children,'__func__',None)is InformationSetForecast.public_children
            and getattr(e.physical_children,'__func__',None)is InformationSetForecast.physical_children
            and getattr(e.project,'__func__',None)is InformationSetForecast.project
            and getattr(e.action_policy._project_roles,'__func__',None)is InformationSetActionPolicy._project_roles)

    def _record_deaths(self,board,payload,target,public,outcomes):
        if not self._canonical_death() or board.initial_hunter_count or not self._observer_supported(payload.observer):return
        qbywinner={o.board.winner:o for o in public}
        self._public_deaths[id(board),id(payload.public_state),id(payload.private),target]=(board,payload,target,public,outcomes)
        for outcome in outcomes:
            q=qbywinner.get(outcome.board.winner)
            if q is not None and outcome.context is q.board:
                self._deaths[id(outcome)]=(_frame(board,payload),target,outcome,q.probability,outcome.probability)

    def can_project(self,board,payload,outcome,target):
        row=self._deaths.get(id(outcome))
        return (self._canonical_death() and self.groups_for(payload.provenance,board,payload) is not None
            and row is not None and row[1]==target and row[2] is outcome
            and _same_references(row[0],_frame(board,payload)))

    def finish_death(self,board,payload,outcome,target,child):
        if not self.can_project(board,payload,outcome,target):return None
        row=self._deaths[id(outcome)];groups=self._fix(self.groups_for(payload.provenance,board,payload),(target,))
        night=board.phase=='night'
        receipt=self._mint_transition(payload,child,groups,'fixed_target_death',row[3],row[4],
            'corpse_compatibility_then_death' if night else 'execution_death',
            'target_intervention_then_death' if night else 'execution_death')
        if receipt is not None:self.stats['death_group_receipts']+=1
        return receipt

    def public_only_deaths(self,board,payload,target):
        if not self._canonical_death():return ()
        row=self._public_deaths.get((id(board),id(payload.public_state),id(payload.private),target))
        if row is None or not _same_references(_frame(board,row[1]),_frame(board,payload)):return ()
        physical={o.board.winner for o in row[4]}
        return tuple(o for o in row[3] if o.board.winner not in physical)

    def _reports_supported(self):
        from .information_set_forecast import InformationSetForecast
        e=self._engine()
        return (self._supported() and not e.retire_uninformative_scans
            and e.strategy.disclosure_for('seer')=='all' and e.strategy.disclosure_for('medium')=='all'
            and all(getattr(getattr(e,name),'__func__',None)is getattr(InformationSetForecast,name)
                for name in ('generate_morning','generate_publications','publications','project','push')))

    def _record_publications(self,b,q,past,rows):
        if self._reports_supported() and not b.initial_hunter_count:
            self._publications[id(rows)]=(b,q,past,rows)

    def _begin_morning(self,b,q,past):
        if self._reports_supported():self._morning_components[id(b),id(q),id(past)]=[]

    def _record_component(self,b,q,past,outcome,state,rows):
        if not self._reports_supported():return
        record=self._publications.get(id(rows))
        key=id(b),id(q),id(past)
        if key not in self._morning_components:return
        if record is None or not _same_references(record,(outcome.board,state,past,rows)):
            self._morning_components[key]=None;return
        if self._morning_components[key] is not None:
            self._morning_components[key].extend((outcome.probability*w,c,law,p) for w,c,law,p in rows)

    def _record_morning(self,b,q,past,rows):
        if not self._reports_supported() or b.initial_hunter_count:return
        simple=self._publications.get(id(rows))
        valid=simple is not None and _same_references(simple,(b,q,past,rows))
        if not valid:
            components=self._morning_components.get((id(b),id(q),id(past)))
            valid=(components is not None and len(components)==len(rows) and all(a[0]==v[0] and _same_references(a[1:],v[1:]) for a,v in zip(components,rows)))
        if valid:self._mornings[id(rows)]=(b,q,past,rows)

    def _record_push(self,q,p,rows,weighted):
        if not self._reports_supported():return
        source=self._mornings.get(id(rows))
        if source is None or source[1] is not q:return
        self._report_batches[id(q),id(p),id(rows)]=(q,p,rows,weighted)
        for mass,c,law,past,own in weighted:
            matches=[r for r in rows if _same_references(r[1:],(c,law,past))]
            if len(matches)==1:
                self._weighted_reports[id(c),id(law),id(past),id(own)]=(source,p,matches[0][0],mass,(c,law,past,own))

    def can_report(self,source,child):
        if not self._reports_supported() or not self._observer_supported(source.observer):return False
        if self.groups_for(source.provenance,source.public,source) is None:return False
        row=self._weighted_reports.get((id(child.public),id(child.public_state),id(child.past),id(child.private)))
        return (row is not None and _same_references(row[0][:3],(source.public,source.public_state,source.past))
            and row[1] is source.private and _same_references(row[4],(child.public,child.public_state,child.past,child.private)))

    def finish_report(self,source,child):
        if not self.can_report(source,child):return None
        row=self._weighted_reports[id(child.public),id(child.public_state),id(child.past),id(child.private)]
        fixed=set()
        for r in set(child.public.reports)-set(source.public.reports):fixed.update((r.reporter,r.target))
        for r in set(child.past)-set(source.past):fixed.update((r.player,r.target))
        for day,actor,target in set(child.public.report_resolved)-set(source.public.report_resolved):fixed.update((actor,target))
        groups=self._fix(self.groups_for(source.provenance,source.public,source),fixed)
        receipt=self._mint_transition(source,child,groups,'uniform_morning_observation',row[2],row[3],
            'configured_uniform_morning','observer_report_likelihood_transfer')
        if receipt is not None:self.stats['report_group_receipts']+=1
        return receipt

    def public_only_reports(self,source,rows):
        if not self._reports_supported():return ()
        generated=self._mornings.get(id(rows))
        if generated is None or not _same_references(generated[:3],(source.public,source.public_state,source.past)):return ()
        record=self._report_batches.get((id(source.public_state),id(source.private),id(rows)))
        if record is None or not _same_references(record[:3],(source.public_state,source.private,rows)):return ()
        positive={(id(c),id(law),id(past)) for mass,c,law,past,p in record[3]}
        return tuple(r for r in rows if tuple(map(id,r[1:])) not in positive)


    @staticmethod
    def _observer_supported(observer):
        from .actor_information import PersonalInformation
        from .seer_intervention import SeerObserver
        from .seer_acquisition import Acquisition
        if observer is None:return True
        return (type(observer) in (PersonalInformation,SeerObserver)
            and type(observer.acquisitions)is tuple
            and all(type(a)is Acquisition and a.player==observer.actor for a in observer.acquisitions)
            and type(observer.actor)is int and observer.actor>0
            and (type(observer)is PersonalInformation or type(observer.target)is int and observer.target>0))

    @staticmethod
    def _observer_positions(observer):
        if observer is None:return ()
        return (observer.actor,*(a.target for a in observer.acquisitions),*((observer.target,) if hasattr(observer,'target') else ()))

    def _record_observed(self,board,before,generated,after,observer,mass):
        if not self._supported() or not self._observer_supported(observer) or not self._generation(board,before,generated):return
        self._observed_generations[id(board),id(before),id(after),id(observer)]=(board,before,after,observer,mass)
        if self._canonical_laws.get(id(generated)) is generated:self._canonical_laws[id(after)]=after
        self.stats['observed_acquisition_records']+=1

    def _observed_generation(self,board,before,after,observer):
        row=self._observed_generations.get((id(board),id(before),id(after),id(observer)))
        return row is not None and _same_references(row[:4],(board,before,after,observer))

    def _record_information_output(self,source,child,information,mass):
        self._information_outputs[id(child)]=(source,child,information,mass)
        self.stats['information_semantic_hypothesis_visits']+=len(source.private.hypotheses)

    def finish_information(self,source,child,information,mass):
        from .actor_information import WolfInformation,PersonalInformation
        from .seer_intervention import SeerObserver
        record=self._information_outputs.get(id(child))
        if record is None or not _same_references(record,(source,child,information,mass)):return None
        if self.groups_for(source.provenance,source.public,source) is None:return None
        if source.public.initial_hunter_count or not self._observer_supported(source.observer) or type(information) not in (WolfInformation,PersonalInformation,SeerObserver):return None
        if type(information)is WolfInformation:
            positions=tuple(p for p in range(1,source.public.player_count+1) if information.initial_roster&(1<<(p-1)))+tuple(a.target for a in information.attacks)
        else:
            if not self._observer_supported(information):return None
            positions=self._observer_positions(information)
        groups=self._fix(self.groups_for(source.provenance,source.public,source),positions)
        receipt=self._mint_transition(source,child,groups,'owner_information_condition',1,mass,
            'unchanged_public_prior','normalized_owner_information_event')
        if receipt is not None:self.stats['information_group_receipts']+=1
        return receipt


    def _record_policy(self,b,q,past,information,mass,policy):
        self._policy_generations[id(policy)]=(b,q,past,information,mass,policy)
        self.stats['wolf_policy_public_hypothesis_visits']+=len(q.hypotheses)

    def _record_choice(self,source,information,information_mass,target,probability,policy):
        from .information_set_forecast import InformationSetForecast
        e=self._engine()
        if (not self._supported() or e.strategy.night!='random'
            or getattr(e.wolf_policy,'__func__',None)is not InformationSetForecast.wolf_policy
            or self.groups_for(source.provenance,source.public,source) is None):return None
        generated=self._policy_generations.get(id(policy))
        if (generated is None or not _same_references(generated[:3],(source.public,source.public_state,source.past))
            or generated[3]!=information or generated[5] is not policy or (target,probability) not in policy):
            self.stats['unknown_policy_declines']+=1;return None
        receipt=ActorChoiceReceipt(information,information_mass,target,probability,policy,generated[4])
        row=self._groups_record(source.provenance)
        self._selections[receipt]=(_frame(source.public,source),row[2],tuple(vars(receipt).values()))
        self.stats['uniform_choice_receipts']+=1
        return receipt

    def validates_choice(self,receipt,source):
        if type(receipt)is not ActorChoiceReceipt or not self._supported():return False
        row=self._selections.get(receipt)
        return (row is not None and self._owner_current(row[1])
            and _same_references(row[0],_frame(source.public,source))
            and _same_references(row[2],tuple(vars(receipt).values())))


@dataclass(frozen=True,eq=False)
class ActorChoiceReceipt:
    information:object
    information_mass:object
    target:int
    probability:object
    policy:tuple
    public_information_mass:object
