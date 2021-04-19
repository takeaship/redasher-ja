#!/usr/bin/env python
__version__ = '0.1'

import click
from yamlns import namespace as ns
from .redash import Redash
from consolemsg import out, step
from pathlib import Path
from slugify import slugify


config = ns.load("config.yaml")

@click.group()
@click.help_option()
@click.version_option(__version__)
def cli():
    'Manages a git controlled and file based version of Redash dashboards'

@cli.command('list')
def _list():
    redash = Redash(config.url, config.apikey)
    for dashboard in redash.dashboards():
        dashboard = ns(dashboard)
        out("{}: {} \"{}\"", dashboard.id, dashboard.slug, dashboard.name)

@cli.command()
@click.argument('id')
def pull(id):
    redash = Redash(config.url, config.apikey)
    dashboard = ns(redash.dashboard(id))
    dashboard.dump("{}.yaml".format(dashboard.slug))
    click.echo(dashboard.dump())


@cli.command()
def qlist():
    redash = Redash(config.url, config.apikey)
    for query in redash.queries():
        query = ns(query)
        print(query.dump())
        out("{}: \"{}\"", query.id, query.name)

@cli.command()
def ulist():
    redash = Redash(config.url, config.apikey)
    for user in redash.users():
        user = ns(user)
        out("{}: \"{}\"", user.id, user.name)

@cli.command()
@click.argument('id')
def qpull(id):
    """Retrieve a query"""
    redash = Redash(config.url, config.apikey)
    query = ns(redash.query(id))
    #query.dump("{}.yaml".format(query.slug))
    click.echo(query.dump())

@cli.command()
@click.argument(
    "servername",
    #help="The name of the server",
)
@click.argument(
    "url",
    #help="Base url of the server",
)
@click.argument(
    "apikey",
    #help="User API key to be used to access the server",
)
def setup(servername, url, apikey):
    configfile = Path('config.yaml')
    config = ns.load(configfile) if configfile.exists else ns()
    servers = config.setdefault('servers', ns())
    servers[servername] = ns(
        url=url,
        apikey=apikey,
    )
    config.setdefault('defaultserver', servername)
    config.dump(configfile)


def serverConfig(servername=None):
    configfile = Path('config.yaml')
    config = ns.load(configfile) if configfile.exists else ns()
    servername = servername or config.get('defaultserver')
    servers = config.setdefault('servers', ns())
    return servers.get(servername)

@cli.command()
@click.argument(
    "servername",
    required=False,
    #help="The name of the server",
)
def checkout(servername):
    config = serverConfig(servername)
    redash = Redash(config.url, config.apikey)
    repopath = Path('.')
    mapper = Mapper(repopath, servername)

    queriespath = repopath / 'queries'
    queriespath.mkdir(exist_ok=True)

    for query in redash.queries():
        step("Exporting query: {id} - {name}", **query)
        query = ns(redash.query(query['id'])) # full content

        querypath = mapper.track('query', repopath/'queries', query)
        querypath.mkdir(parents=True, exist_ok=True)

        del query.id
        del query.user
        del query.last_modified_by
        query_text = query.pop('query')
        visualizations = query.pop('visualizations',[])
        query.dump(querypath/'metadata.yaml')

        (querypath/'query.sql').write_text(query_text, encoding='utf8')
        for vis in visualizations:
            vis = ns(vis)
            step("Exporting visualization {id} {type} {name}", **vis)
            vispath = mapper.track('visualization', querypath, vis, 'vis-', '.yaml')
            vis.dump(vispath)

    dashboardspath = repopath / 'dashboards'
    dashboardspath.mkdir(exist_ok=True)
    for dashboard in redash.dashboards():
        step("Exporting dashboard: {id} - {name}", **dashboard)

class Mapper(object):
    """Keeps track of the binding among objects in a server
    and a file path.
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
        for slug in self._slugger(anObject.name):
            objecPath = basePath / (prefix+slug+suffix)
            if not objecPath.exists(): break
        objects[anObject.id] = str(objecPath)
        self._save(maps)
        return objecPath

    def bind(self, type, id, path):
        """
        Binds an object id to the path for the server
        """
        maps = self._load()
        objects = maps.setdefault(type, ns())
        objects[id] = str(path)
        self._save(maps)






    
    


if __name__=='__main__':
    cli()

