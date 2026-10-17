"""Request-owned, sparse current-call sampling. No tree or secret serialization."""
import json,secrets,sys
from queue import Queue,Empty,Full
from threading import Event,Thread,get_ident
from time import monotonic
from .calculation_budget import cancellation_scope,CalculationCancelled,tick

MODULES=frozenset(('werewolf.information_set_forecast','werewolf.root_secret_flow','werewolf.exact'))
METHODS=frozenset(('solve','act','uncached_act','owned_night_action','evaluate'))
def current_path(thread_id):
    path=[];frame=board=local=None
    try:
        frame=sys._current_frames().get(thread_id)
        while frame is not None:
            if frame.f_globals.get('__name__') in MODULES and frame.f_code.co_name in METHODS:
                local=frame.f_locals;board=local.get('b',local.get('board'))
                if board is not None and getattr(board,'phase',None) in ('day','night'):
                    path.append({'day':int(board.day),'phase':board.phase})
            frame=frame.f_back
        path.reverse();return len(path),path[-12:]
    finally:del frame,board,local

def position_stream(produce,*,view='public',interval=1.0):
    """One request worker, bounded output, no persistent job registry.

    produce must be wrapped in a COPY of Flask's request context. It owns its
    original budget and process slot. Disconnect cooperatively cancels tick().
    """
    if interval<1:raise ValueError('Position interval must be at least one second')
    messages=Queue(maxsize=2);cancel=Event();finished=Event();run_id=secrets.token_hex(6);identity=None
    done=object();worker_id=[None]
    def put(item):
        while not cancel.is_set():
            try:messages.put(item,timeout=.1);return
            except Full:tick(0)
    def work():
        worker_id[0]=get_ident()
        try:
            with cancellation_scope(cancel):
                def send(chunk):
                    if cancel.is_set():raise CalculationCancelled()
                    put(chunk)
                    if cancel.is_set():raise CalculationCancelled()
                produce(send)
        except CalculationCancelled:pass
        except BaseException as error:put(error)
        finally:
            finished.set()
            try:messages.put_nowait(done)
            except Full:pass
    worker=Thread(target=work,name='ww-calculation-stream',daemon=True);worker.start()
    next_sample=monotonic()+interval;sequence=0;sampling=True
    try:
        while True:
            if finished.is_set() and messages.empty():break
            try:item=messages.get(timeout=max(.001,next_sample-monotonic()))
            except Empty:
                if finished.is_set():continue
                now=monotonic();next_sample=now+interval
                if identity is not None and worker.is_alive() and not finished.is_set():
                    try:depth,path=current_path(worker_id[0]) if sampling else (0,[])
                    except Exception:
                        sampling=False;depth,path=0,[]
                        import logging
                        logging.getLogger('wwgg.budget').warning('wwgg_position_sampling unavailable')
                        yield json.dumps({'event':'position-unavailable','run_id':run_id},separators=(',',':'))+'\n'
                    if finished.is_set():continue
                    if path:
                        sequence+=1
                        event={'event':'position','run_id':run_id,'view':view,**identity,
                               'sample_id':sequence,'depth':depth,'path':path,'truncated':depth>12}
                        yield json.dumps(event,separators=(',',':'))+'\n'
                    else:yield json.dumps({'event':'heartbeat','run_id':run_id},separators=(',',':'))+'\n'
                else:yield json.dumps({'event':'heartbeat','run_id':run_id},separators=(',',':'))+'\n'
                continue
            if item is done:break
            if isinstance(item,BaseException):raise item
            event=json.loads(item)
            event['run_id']=run_id;event['view']=view
            if event.get('event')=='roles':
                identity={key:event[key] for key in ('board_id','revision','request_id') if key in event}
            if event.get('event') in ('complete','error'):identity=None
            yield json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'
    finally:
        cancel.set();worker.join(timeout=2)
        # Worker keeps ownership of its slot until its budget/finally ends.
        # No slot is released early to permit a duplicate concurrent calculation.
        if worker.is_alive():
            import logging
            logging.getLogger('wwgg.budget').warning('wwgg_position_cleanup pending_worker=true')
