"""Private cursor HTTP boundary. Public navigation is never mutated."""
from hashlib import sha256
import json
from flask import request,jsonify
from .guard_view_document import GuardViewDocument
from .information_set_forecast import Pending

def key(record):
 return sha256(json.dumps({k:record[k] for k in ('owner','anchor','role','players','results','target')},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def remember(public,view):
 views=getattr(public,'private_views',None)
 if views is None:views={};public.private_views=views
 views[key(view.export())]=view
 return view

def register(app,document,render,public_render):
 @app.post('/private-navigation')
 def private_navigation():
  try:
   public=document();payload=request.get_json()
   if type(payload)is not dict or set(payload)-{'view','operation','node','expand','analysis','snapshot','public_revision'}:raise ValueError('Private navigation input required')
   if type(payload.get('public_revision'))is not int or payload['public_revision']!=public.revision:return jsonify(error='Public Board changed'),409
   operation=payload.get('operation','tree')
   if operation=='public':return jsonify(html=public_render(public),private_view=None)
   record=payload.get('view')
   if type(record)is not dict:raise ValueError('Private evidence required')
   with public.lock:
    views=getattr(public,'private_views',{});view=views.get(key(record))
    if view is None:view=remember(public,GuardViewDocument.restore(public,record))
    elif json.dumps(record,sort_keys=True)!=json.dumps(view.export(),sort_keys=True):return jsonify(error='Private view changed'),409
   with view.lock:
    tree=view.tree()
    if payload.get('snapshot') not in (None,tree.snapshot):return jsonify(error='Private snapshot changed'),409
    if operation=='tree':
     if type(payload.get('expand',False))is not bool or type(payload.get('analysis',False))is not bool:raise ValueError('Boolean Tree options required')
     result=tree.read(payload.get('node'),payload.get('expand',False),payload.get('analysis',False))
    elif operation in ('current','back','forward','restore'):
     original=view.game;revision=view.revision;view.game=original.fork()
     try:
      if operation=='current':tree.select(payload['node'])
      elif operation=='back':view.game.back()
      elif operation=='forward':view.game.forward()
      view.revision+=operation!='restore'
      result=dict(html=render(view),current_node=tree.current_key())
     except Exception:
      view.game=original;view.revision=revision;view.views=None
      raise
    else:raise ValueError('Unknown private navigation operation')
    result.update(private_view=view.export(),public_revision=public.revision)
    return jsonify(result)
  except Pending as exc:return jsonify(error=exc.reason,unsupported=True),422
  except (ValueError,TypeError,KeyError) as exc:return jsonify(error=str(exc)),400
