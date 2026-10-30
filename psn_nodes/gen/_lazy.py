"""Import a heavy library on first use, so loading the pack stays fast. Not a node module: gen.load() skips names starting with an underscore."""
import importlib

class LazyModule:
    def __init__(self, name, setup=None): self.__dict__.update(_name=name, _setup=setup, _mod=None)
    def __getattr__(self, attr):
        if self._mod is None:
            if self._setup: self._setup()
            self.__dict__["_mod"] = importlib.import_module(self._name)
        return getattr(self._mod, attr)
