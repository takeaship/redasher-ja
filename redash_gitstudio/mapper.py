from yamlns import namespace as ns
from pathlib import Path
from slugify import slugify

class Mapper(object):
    """Keeps track of the binding of server objects
    with file paths.
    """
    def __init__(self, repopath, servername):
        self.repopath = repopath
        self.servername = servername
        self.mapfile = self.repopath/'maps'/'{}.yaml'.format(servername)

    def _load(self):
        if not self.mapfile.exists():
            return ns()
        return ns.load(self.mapfile)

    def _save(self, content):
        self.mapfile.parent.mkdir(exist_ok=True)
        content.dump(self.mapfile)

    def _slugger(self, base):
        "Returns first the slug as is, then adding sequence numbers"
        slug = slugify(base)
        from itertools import count
        yield slug
        for c in count(2):
            yield slug + "-{}".format(c)

    def track(self, type, basePath, anObject, prefix='', suffix=''):
        """
        Lookups in the server if the object id already has a file mapping.
        If not, looks one that does not exists and returns the path.
        """
        maps = self._load()
        objects = maps.setdefault(type, ns())
        if anObject.id in objects:
            return Path(objects[anObject.id])
        for slug in self._slugger(anObject.get('name', type)):
            objectPath = basePath / (prefix+slug+suffix)
            if not objectPath.exists(): break
        objects[anObject.id] = str(objectPath)
        self._save(maps)
        return objectPath

    def bind(self, type, id, path):
        """
        Binds an object id to the path for the server
        """
        maps = self._load()
        objects = maps.setdefault(type, ns())
        objects[id] = str(path)
        self._save(maps)

    def get(self, type, id):
        maps = self._load()
        objects = maps.setdefault(type, ns())
        return objects.get(id)

    def remoteId(self, type, path):
        maps = self._load()
        objects = maps.setdefault(type, ns())
        inversemap = {v:k for k,v in objects.items()}
        return inversemap.get(str(path), None)


