"""Opt-in browser-owned recipes over the ordinary navigation HTTP handlers.

No database, durable job, client payoff trust, or second game simulator.
"""
import io,json,hashlib,base64
from copy import deepcopy
from urllib.parse import urlsplit,parse_qsl,urlencode
from flask import request,session,g,jsonify
from itsdangerous import URLSafeSerializer,BadSignature
from .navigation_store import NavigationStore,NavigationDocument
from .information_set_forecast import Pending

LIMIT=131072
ALLOWED={'/navigation','/navigation/calculation','/game-tree','/game-tree/current','/table-preview','/table-publish','/private-view','/private-navigation','/strategy'}
OPERATIONS={'move','back','forward','advance','phase-back','phase-next','public-input'}

class BrowserStore(NavigationStore):
    def get(self,identity,data):
        if not hasattr(g,'browser_document'):
            g.browser_document=NavigationDocument(data,anonymous_owned=self.anonymous_owned)
        return g.browser_document
    def save(self,identity,document):
        # Persistence belongs to the IndexedDB commit before installing the UI.
        g.browser_document=document


def install(app):
    signer=URLSafeSerializer(app.secret_key,salt='browser-history-prototype-v1')
    def token(doc):return signer.dumps(doc.export())
    original=app.wsgi_app
    def transport(environ,start_response):
        if environ.get('PATH_INFO')!='/browser-history/request':return original(environ,start_response)
        def fail(message,code='400 Bad Request'):
            data=json.dumps({'error':message}).encode();start_response(code,[('Content-Type','application/json'),('Content-Length',str(len(data)))]);return [data]
        try:
            if environ.get('REQUEST_METHOD')!='POST':return fail('POST required','405 Method Not Allowed')
            origin=environ.get('HTTP_ORIGIN')
            if environ.get('HTTP_SEC_FETCH_SITE')=='cross-site' or origin and origin!=environ.get('wsgi.url_scheme','http')+'://'+environ.get('HTTP_HOST',''):return fail('Cross-site request rejected','403 Forbidden')
            length=int(environ.get('CONTENT_LENGTH') or 0)
            if not 0<length<=LIMIT:return fail('Browser recipe request is too large','413 Payload Too Large')
            packet=json.loads(environ['wsgi.input'].read(length))
            if type(packet)is not dict or set(packet)!={'url','method','body','content_type','token','routes'}:raise ValueError('Invalid browser transport')
            u=urlsplit(packet['url']);path=u.path
            if u.scheme or u.netloc or not(path in ALLOWED or path.startswith('/navigation/') and path.rsplit('/',1)[1] in OPERATIONS):raise ValueError('Invalid browser route')
            if type(packet['url'])is not str or type(packet['content_type'])is not str:raise ValueError('Invalid transport types')
            method=packet['method']
            if method not in ('GET','POST') or type(packet['body'])is not str or type(packet['token'])is not str or type(packet['routes'])is not dict:raise ValueError('Invalid browser request')
            body=packet['body'].encode()
            if len(body)>4096:raise ValueError('Operation input too large')
            environ.update(PATH_INFO=path,QUERY_STRING=u.query,REQUEST_METHOD=method,CONTENT_LENGTH=str(len(body)),CONTENT_TYPE=packet['content_type'],**{'wsgi.input':io.BytesIO(body),'wwgg.browser_packet':packet})
        except (ValueError,TypeError,KeyError):return fail('Invalid browser transport')
        if environ.get('HTTP_X_WW_BROWSER_STREAM')!='1':return original(environ,start_response)
        # Keep the transport connection writable even during recipe replay or a
        # JSON Tree handler. Its request-owned Event reaches the same tick().
        from .exploration_position import position_stream
        def produce(send):
            def headers(status,items,exc_info=None):
                send(json.dumps(dict(event='browser-headers',status=int(status.split()[0]),headers=[(k,v) for k,v in items if k.lower() not in ('set-cookie','content-length','transfer-encoding')]))+'\n')
            source=original(environ,headers)
            try:
                for chunk in source:send(json.dumps(dict(event='browser-chunk',data=base64.b64encode(chunk).decode()))+'\n')
            finally:
                if hasattr(source,'close'):source.close()
        start_response('200 OK',[('Content-Type','application/x-ndjson'),('Cache-Control','no-store'),('X-WW-Browser-Stream','1')])
        source=position_stream(produce)
        def encoded():
            try:
                for chunk in source:yield chunk.encode('utf-8')
            finally:source.close()
        return encoded()
    app.wsgi_app=transport

    @app.before_request
    def restore_browser_document():
        packet=request.environ.get('wwgg.browser_packet')
        if packet is None:
            if request.method=='POST' and request.path not in ('/start','/calculation-cancel'):return jsonify(error='Browser-history prototype requires its public recipe transport'),422
            return
        try:
            record=signer.loads(packet['token'])
            if type(record)is not dict or set(record)-{'version','root','revision','history','anonymous_owned'}:raise ValueError('Invalid browser recipe')
            from .calculation_budget import calculation_budget,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
            with calculation_budget(app.config.get('MANUAL_CALC_MAX_WORK',DEFAULT_MAX_WORK),max_seconds=app.config.get('MANUAL_CALC_MAX_SECONDS',DEFAULT_MAX_SECONDS)):
                doc=NavigationDocument.restore(record)
            g.browser_document=doc
            g.browser_session=deepcopy(dict(session));g.browser_session_modified=session.modified
            from .navigation_current import NavigationCurrent
            session['game']=NavigationCurrent(doc.game).data.to_game()
            # The existing cookie scopes request cancellation; it is not history storage.
            from .navigation_tree import NavigationTree
            private=None
            if request.path=='/private-navigation':
                body=request.get_json()
                if type(body)is not dict:raise ValueError('Private input required')
                if body.get('operation')!='public':
                    from .personal_navigation_http import restore_view
                    private=restore_view(doc,body.get('view'));g.browser_private_view=private
            if packet['routes']:
                view=private.tree() if private is not None else NavigationTree(doc)
                if private is None:doc.views=view
                aliases={}
                for key,signed in packet['routes'].items():
                    ref=signer.loads(signed)
                    scope='public' if private is None else private.anchor
                    if ref['revision']!=doc.revision or ref['key']!=key or ref.get('scope','public')!=scope or ref.get('private_revision',0)!=(private.revision if private is not None else 0):raise ValueError('Stale or different-view Tree recipe')
                    tree,names=view.view(ref['owner']);local=tree.restore(ref['route']);aliases[key]=view.key(ref['owner'],local)
                query=[(k,aliases.get(v,v) if k=='node' else v) for k,v in parse_qsl(request.query_string.decode(),keep_blank_values=True)]
                request.environ['QUERY_STRING']=urlencode(query);request.query_string=urlencode(query).encode();request.__dict__.pop('args',None)
                if request.path=='/private-navigation':
                    body=dict(body);body['node']=aliases.get(body.get('node'),body.get('node'));g.browser_private_payload=body
                if request.path=='/game-tree/current':
                    form=request.form.copy();form['node']=aliases.get(form.get('node'),form.get('node'));request.__dict__['form']=form
        except Pending as exc:
            return jsonify(error=exc.reason,unsupported=True),422
        except (BadSignature,ValueError,TypeError,KeyError,IndexError) as exc:
            return jsonify(error='Invalid or incompatible browser history: '+str(exc)),400

    @app.after_request
    def export_browser_document(response):
        packet=request.environ.get('wwgg.browser_packet');doc=getattr(g,'browser_document',None)
        if packet is not None and doc is not None and response.is_json and response.status_code<300:
            data=response.get_json();mapping={};routes={}
            private=getattr(g,'browser_private_view',None)
            view=private.tree() if private is not None else getattr(doc,'views',None)
            scope='public' if private is None else private.anchor
            prefix='' if private is None else 'private:'+scope+':'
            if view is not None:
                for owner,(tree,names) in tuple(view.views.items()):
                    for local in tuple(tree.nodes):
                        route=tree.route(local);key=prefix+owner+'~'+('0' if not route else hashlib.sha256(json.dumps(route,sort_keys=True).encode()).hexdigest()[:20])
                        mapping[view.key(owner,local)]=key
                        routes[key]=signer.dumps(dict(key=key,owner=owner,route=route,revision=doc.revision,scope=scope,private_revision=private.revision if private is not None else 0))
            def remap(value):
                if isinstance(value,str):return mapping.get(value,value)
                if isinstance(value,list):return [remap(v) for v in value]
                if isinstance(value,dict):return {mapping.get(k,k):(v if k=='private_view' else remap(v)) for k,v in value.items()}
                return value
            data=remap(data);data['browser_history']=token(doc);data['browser_routes']=routes;data['browser_revision']=doc.revision
            response.set_data(app.json.dumps(data));response.headers['Cache-Control']='no-store'
        if hasattr(g,'browser_session'):
            session.clear();session.update(g.browser_session);session.modified=g.browser_session_modified
        return response

    @app.context_processor
    def seed():
        doc=getattr(g,'browser_document',None)
        return {'browser_history_seed':dict(token=token(doc),game=session.get('co_display_game'),revision=doc.revision) if doc is not None else None}
