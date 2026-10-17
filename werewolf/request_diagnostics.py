"""Opt-in bounded lifecycle logs: no game, session, request payload or headers."""
from datetime import datetime, timezone
from time import monotonic
import json, logging, secrets

_PROCESS = secrets.token_hex(6)
_EVENTS = frozenset(('request_enter','request_wait','request_acquired','request_released','worker_enter','worker_exit','stream_wait','stream_acquired','stream_released','stream_exit','iterator_exit','cancel_set','join_done'))
_REASONS = frozenset(('complete','cancelled','closed','error','time','work'))

class RequestTrace:
    def __init__(self, endpoint):
        self.request_id = secrets.token_hex(8)
        self.endpoint = endpoint if endpoint in ('main','start','private_view','table_publish','table_preview','advance','comparison') else 'other'
        self.started = monotonic()
    def emit(self, event, *, reason=None, pending=None):
        try:
            if event not in _EVENTS:return
            data = {'event':event,'at':datetime.now(timezone.utc).isoformat(timespec='milliseconds'),'elapsed_ms':round((monotonic()-self.started)*1000,3),'request':self.request_id,'process':_PROCESS,'endpoint':self.endpoint}
            if reason in _REASONS:data['reason']=reason
            if type(pending) is bool:data['pending']=pending
            logging.getLogger('wwgg.lifecycle').warning('wwgg_lifecycle %s',json.dumps(data,separators=(',',':')))
        except Exception:pass
