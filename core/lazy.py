"""Load optional action modules only when an action is actually requested."""
from importlib import import_module
import threading

class LazyAction:
    def __init__(self,module,name):
        self.module,self.name=module,name
        self._function=None
        self._lock=threading.Lock()
    def __call__(self,*args,**kwargs):
        if self._function is None:
            with self._lock:
                if self._function is None:
                    self._function=getattr(import_module(self.module),self.name)
        return self._function(*args,**kwargs)
