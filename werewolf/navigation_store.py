"""Small local evidence journals; solver states and secrets are reconstructed.

One document per existing game identity, outside cookies. Atomic replacement
keeps the complete append-only occurrence history. No evaluations are serialized.
"""
from pathlib import Path
from hashlib import sha256
from threading import RLock
import json,os,tempfile
from .board_flow import BoardData
from .closed_calculation import ClosedCalculation
from .navigation_game import NavigationGame

class StaleNavigation(ValueError):pass

class NavigationDocument:
    def __init__(self,data,game=None,revision=0):
        self.data=data;self.revision=revision;self.lock=RLock()
        self.game=game or NavigationGame(ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root)
    def export(self):return dict(version=1,root=self.data.to_game(),revision=self.revision,history=self.game.export())
    @classmethod
    def restore(cls,record):
        if record.get('version')!=1:raise ValueError('Unsupported navigation document')
        data=BoardData.from_game(record['root']);root=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root
        return cls(data,NavigationGame.restore(root,record['history']),record['revision'])

class NavigationStore:
    def __init__(self,directory):self.directory=Path(directory);self._documents={};self._lock=RLock()
    def _path(self,identity):return self.directory/(sha256(identity.encode()).hexdigest()+'.json')
    def get(self,identity,data):
        with self._lock:
            if identity in self._documents:return self._documents[identity]
            path=self._path(identity)
            doc=NavigationDocument.restore(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else NavigationDocument(data)
            self._documents[identity]=doc;return doc
    def save(self,identity,document):
        self.directory.mkdir(parents=True,exist_ok=True)
        text=json.dumps(document.export(),sort_keys=True,separators=(',',':'),allow_nan=False)
        handle,name=tempfile.mkstemp(prefix='navigation-',suffix='.tmp',dir=self.directory)
        try:
            with os.fdopen(handle,'w',encoding='utf-8') as stream:stream.write(text)
            os.replace(name,self._path(identity))
        finally:
            if os.path.exists(name):os.unlink(name)
    def apply(self,identity,data,revision,action):
        doc=self.get(identity,data)
        with doc.lock:
            if revision!=doc.revision:raise StaleNavigation('Navigation changed; reload the current Board')
            # Restore the cursor/occurrences if validation or persistence fails.
            # Atomic replacement is the commit boundary; an exception before it
            # must not leave an invisible successful mutation in this process.
            before=doc.game.export();old_revision=doc.revision
            try:
                result=action(doc.game);doc.revision+=1;self.save(identity,doc)
            except Exception:
                doc.game=NavigationGame.restore(doc.game.history.state(doc.game.history.root).node,before)
                doc.revision=old_revision
                raise
            return doc,result
