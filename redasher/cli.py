#!/usr/bin/env python
__version__ = '0.1'

import click
from pathlib import Path
from yamlns import namespace as ns
from consolemsg import out, warn, step, fail
from .redash import Redash
from .mapper import Mapper
from .repo import (
    serverConfig,
    setServerConfig,
    defaultServer,
    setDefaultServer,
    checkoutAll,
    uploadFile,
)



@click.group()
@click.help_option()
@click.version_option(__version__)
def cli():
    'Manages a git controlled and file based version of Redash dashboards'

@cli.command('list')
def _list():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for dashboard in redash.dashboards():
        dashboard = ns(dashboard)
        out("{}: {} \"{}\"", dashboard.id, dashboard.slug, dashboard.name)

@cli.command()
@click.argument('id')
def pull(id):
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    dashboard = ns(redash.dashboard(id))
    dashboard.dump("{}.yaml".format(dashboard.slug))
    click.echo(dashboard.dump())


@cli.command()
def qlist():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for query in redash.queries():
        query = ns(query)
        print(query.dump())
        out("{}: \"{}\"", query.id, query.name)

@cli.command()
def ulist():
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    for user in redash.users():
        user = ns(user)
        out("{}: \"{}\"", user.id, user.name)

@cli.command()
@click.argument('id')
def qpull(id):
    """Retrieve a query"""
    config = serverConfig()
    redash = Redash(config.url, config.apikey)
    query = ns(redash.query(id))
    #query.dump("{}.yaml".format(query.slug))
    click.echo(query.dump())

@cli.command()
@click.argument("servername")
@click.argument("url")
@click.argument("apikey")
def setup(servername, url, apikey):
    """Configures a Redash server to work with.

    SERVERNAME is the name setup for the server.
    URL is the base url for the server.
    APIKEY is the validation key related to the user
    the program is going to act in behalf on.

    If no default server has been configured this
    server will be considered default.
    """
    setServerConfig(servername, url, apikey)

@cli.command()
@click.argument("servername", required=False)
def default(servername=None):
    """Sets or shows the default server name to work with.

    Shows instead of setting it, if no SERVERNAME is provided.
    """
    if servername:
        setDefaultServer(servername)
        return
    servername = defaultServer()
    if not servername:
        fail("No default server defined")
    print(servername)


@cli.command()
@click.argument("servername")
@click.argument("type")
@click.argument("file")
@click.argument("id", type=int)
def bind(servername, type, id, file):
    """Relates a file object FILE to an ID of type TYPE in SERVER"""
    configfile = serverConfig(servername)
    repopath = Path('.')
    mapper = Mapper(repopath, servername)
    oldfile = mapper.get(type, id)
    if oldfile:
        warn("Id {} in {} was bound to {}".format(
            id, servername, oldfile
        ))
    mapper.bind(type, id, file)


@cli.command()
@click.argument("servername")
def checkout(servername):
    """Downloads all objects from a Redash server"""
    checkoutAll(servername)

@cli.command()
@click.argument("servername")
@click.argument("objectfile", type=Path, nargs=-1)
def upload(servername, objectfile):
    "Upload a dashboard and all dependant objects"
    uploadFile(servername, *objectfile)



if __name__=='__main__':
    cli()

