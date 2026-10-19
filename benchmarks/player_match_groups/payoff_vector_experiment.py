"""DEVELOPMENT full-horizon root-secret payoff vectors, H0/fixed CO only.

The scalar engine still owns public/actor Q strategy selection. Common physical,
acquisition, report, wolf partition and cold flows are reused without replacing
policy. Only actual-P continuation accumulation is vector-valued.
"""
from dataclasses import replace
from fractions import Fraction as F
from werewolf.calculation_budget import tick
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.exact import legal_targets
from werewolf.policy_choice import optimal_targets
from werewolf.forecast_result import Forecast
from werewolf.model_a_public import horizon_for_action
from werewolf.seer_intervention import SeerObserver


class PayoffVectorExperiment:
    def __init__(self,calculation):
        self.calculation=calculation;self.root=calculation.root.read();self.e=calculation._ClosedCalculation__engine
        b=self.root.public
        if b.day!=1 or b.phase!='day' or b.history or b.initial_hunter_count or b.initial_medium_count:raise ValueError('Initial fixed-CO H0 scope only')
        if self.root.private!=self.root.public_state:raise ValueError('Public complete root prior required')
        self.initial_day=b.day;self.basis=tuple(self.fiber(h) for h in self.root.private.hypotheses)
        self.index={key:i for i,key in enumerate(self.basis)};self.prior=tuple(h.mass for h in self.root.private.hypotheses)
        self.width=len(self.basis);self.values={};self.actions={};self.distributions={};self.fallbacks=0
        self.counts={'solve_calls':0,'action_calls':0,'terminal_branches':0,'report_branches':0,'physical_branches':0}

    @staticmethod
    def fiber(h):return h.roles,h.acquisitions,h.guards,h.attacks
    def zero(self):return (F(),)*self.width
    def add(self,left,right,weight=F(1)):
        tick(self.width)
        return tuple(a+weight*b for a,b in zip(left,right))
    def ancestor(self,h):
        key=(h.roles,tuple(a for a in h.acquisitions if a.day<=self.initial_day),
            tuple(g for g in h.guards if g.night<self.initial_day),tuple(a for a in h.attacks if a.night<self.initial_day))
        return self.index[key]

    def distribution(self,state):
        if state in self.distributions:return self.distributions[state]
        out=list(self.zero())
        for h in state.hypotheses:
            tick()
            out[self.ancestor(h)]+=h.mass
        self.distributions[state]=tuple(out);return tuple(out)

    def solve(self,s):
        self.counts['solve_calls']+=1
        if s in self.values:return self.values[s]
        b=s.public;e=self.e
        with e.frame_scope(b,s.past,s.observer):
            if b.winner is not None:
                result=self.distribution(s.private) if b.winner=='village' else self.zero()
            else:
                result=self.zero()
                if b.phase=='day':
                    targets=b.alive if e.strategy.day=='random' else optimal_targets(e.day_scores(b,s.public_state,s.past),maximize=True)
                    for target in targets:result=self.add(result,self.act(s,target),F(1,len(targets)))
                else:
                    for mass,child,target,unused in e.wolf_choices(s):
                        result=self.add(result,self.act(child,target),mass)
        self.values[s]=result;return result

    def act(self,s,target):
        self.counts['action_calls']+=1;key=(s,target)
        if key in self.actions:return self.actions[key]
        e=self.e;b=s.public;result=self.zero()
        with e.frame_scope(b,s.past,s.observer,target=target):
            # SAME acquisition/death order as scalar action_flow. No preflight,
            # truncation or future report deletion is introduced.
            payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
            acquired,outcomes=resolve_action(b,payload,target,e.action_policy,terminal_payoffs=False)
            for outcome in outcomes:
                self.counts['physical_branches']+=1
                if outcome.board.winner is not None:
                    self.counts['terminal_branches']+=1
                    own=e.project(acquired.private,outcome.board)
                    value=self.distribution(own) if outcome.board.winner=='village' else self.zero()
                else:
                    child=e.action_policy.project(b,acquired,outcome,target)
                    if b.phase=='night':
                        if e.terminal_execution_day(child.public):value=self.terminal_moments(child)
                        else:
                            value=self.zero()
                            for q,mass,reported in e.report_children(child):
                                self.counts['report_branches']+=1
                                value=self.add(value,self.solve(reported),mass)
                    else:value=self.solve(child)
                result=self.add(result,value,outcome.probability)
        self.actions[key]=result;return result

    def terminal_moments(self,s):
        # Reuse the EXISTING complete public-Q terminal moment formula/cache;
        # only scatter its P-weighted fibers to initial secret coordinates.
        from werewolf.information_weights import observer_projection_ratios
        from werewolf.information_set_forecast import Pending
        incomplete=lambda:Pending('information_set_report_likelihood_incomplete')
        e=self.e;k=e.publication_kernel(s.public,s.public_state,s.past);targets=tuple(s.public.alive)
        observer_projection_ratios(s.public_state,s.private,incomplete=incomplete)
        tick(0);key=(k,targets);moments=e.terminal_moments.get(key)
        if moments is None:
            moments=k.terminal_execution_moments(targets,incomplete=incomplete);e.terminal_moments.put(key,moments)
        public={}
        for h in s.public_state.hypotheses:
            tick();fiber=(h.roles,h.acquisitions);public[fiber]=public.get(fiber,F())+h.mass
        values=dict(moments);out=list(self.zero())
        for h in s.private.hypotheses:
            tick();fiber=(h.roles,h.acquisitions)
            out[self.ancestor(h)]+=h.mass*values.get(fiber,F())/public[fiber]
        self.counts['terminal_moment_applications']=self.counts.get('terminal_moment_applications',0)+1
        return tuple(out)

    def apply(self,vector,private):
        weights={self.fiber(h):h.mass for h in private.hypotheses}
        if not set(weights)<=set(self.index):raise ValueError('Owner private input outside root support')
        tick(self.width)
        return sum((weights.get(key,F())*vector[i]/self.prior[i] for i,key in enumerate(self.basis)),F())

    def forecast(self,node):
        if node._Node__calculation is not self.calculation:raise ValueError('Same immutable calculation only')
        s=node.read()
        # Future acquisition interventions can renormalize P differently. They
        # KEEP their exact scalar behavior; never alias them to this operator.
        if type(s.observer)is SeerObserver:
            self.fallbacks+=1;return node.forecast()
        if (s.public,s.public_state,s.past)!=(self.root.public,self.root.public_state,self.root.past):raise ValueError('Same root observation required')
        e=self.e
        with self.calculation._ClosedCalculation__kernel(),e.group_scope(self.calculation.root.groups):
            v=self.solve(self.root);targets=legal_targets(s.physical,e.rules,e.strategy)
            values=tuple((t,self.apply(self.act(self.root,t),s.private)) for t in targets)
            # By-dawn is a separate existing output and remains exact common
            # scalar horizon evaluation; cost is included in all measurements.
            dawn=tuple((t,horizon_for_action(e,s.public,s.public_state,s.past,t,s.private,observer=s.observer)) for t in targets)
            return Forecast(self.apply(v,s.private),values,dawn)

    def stats(self):
        vectors=tuple(self.values.values())+tuple(self.actions.values())+tuple(self.distributions.values())
        return {'width':self.width,'value_vectors':len(self.values),'action_vectors':len(self.actions),
            'distribution_vectors':len(self.distributions),'stored_coefficients':sum(map(len,vectors)),
            'nonzero_coefficients':sum(sum(bool(x) for x in v) for v in vectors),'future_scalar_fallbacks':self.fallbacks,**self.counts}
