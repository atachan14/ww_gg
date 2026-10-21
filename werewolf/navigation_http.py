"""Local HTTP boundary for the persistent navigation owner.

External clients submit a revision and semantic action, never solver posteriors,
policy weights, or arbitrary name maps. Ordinary Board rendering is supplied by
its existing application adapter rather than duplicated here.
"""
from flask import Blueprint,request,jsonify
from fractions import Fraction
from .navigation_current import NavigationCurrent
from .navigation_store import StaleNavigation
from .manual_public_input import UnsupportedPublicInput,ContradictoryPublicInput
from .seer_acquisition import SeerReport
from .information_set_forecast import Pending

def register_navigation(app,store,owner):
    bp=Blueprint('navigation',__name__)
    def document():
        if not app.config.get('PERSISTENT_TREE_PREVIEW'):return None
        identity,data=owner()
        if identity is None:raise ValueError('Start a game first')
        return identity,data,store.get(identity,data)
    def summary(doc):
        current=NavigationCurrent(doc.game);row=doc.game.occurrence
        forecast=current.roles.forecast() if not current.roles.progress.finished else None
        total=current.roles.progress.total_values(forecast)
        return dict(revision=doc.revision,current=current.metadata,root=doc.game.history.root,
            path=[r.key for r in doc.game.history.path(row.key)],
            occurrences=[dict(key=r['key'],parent=r['parent'],edge_kind=r['edge_kind'],selection_weight=r['selection_weight']) for r in doc.game.history.export()],
            board=dict(day=current.roles.board.day,phase=current.roles.board.phase,alive=list(current.roles.board.alive),claims=list(current.roles.board.claims)),
            village_win=str(total.village_win))
    @bp.get('/navigation')
    def read():
        try:
            owned=document()
            if owned is None:return jsonify(error='Not enabled'),404
            with owned[2].lock:return jsonify(summary(owned[2]))
        except Pending as exc:return jsonify(error=exc.reason,unsupported=True),422
        except ValueError as exc:return jsonify(error=str(exc)),400
    @bp.post('/navigation/<operation>')
    def mutate(operation):
        try:
            owned=document()
            if owned is None:return jsonify(error='Not enabled'),404
            payload=request.get_json()
            if type(payload)is not dict or type(payload.get('revision'))is not int:raise ValueError('Navigation revision required')
            allowed={'move':{'occurrence'},'back':set(),'forward':{'occurrence'},'advance':{'target','outcome'},'public-input':{'claims','reports'}}
            if operation not in allowed:return jsonify(error='Unknown navigation operation'),404
            if set(payload)-({'revision'}|allowed[operation]):raise ValueError('Unknown navigation field')
            def action(game):
                if operation=='move':return game.move(payload['occurrence'])
                if operation=='back':return game.back()
                if operation=='forward':return game.forward(payload.get('occurrence'))
                if operation=='advance':return game.action(payload['target'],outcome=payload.get('outcome'))
                reports=tuple(SeerReport(**r) for r in payload.get('reports',()))
                return game.public_input(tuple(payload['claims']),reports)
            identity,data,doc=owned
            doc,row=store.apply(identity,data,payload['revision'],action)
            with doc.lock:return jsonify(summary(doc))
        except StaleNavigation as exc:return jsonify(error=str(exc),stale=True),409
        except Pending as exc:return jsonify(error=exc.reason,unsupported=True),422
        except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc)),400
    app.register_blueprint(bp)
