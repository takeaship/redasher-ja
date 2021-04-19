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
    print(config.dump())
    redash = Redash(config.url, config.apikey)
    queries = redash.queries()
    repopath = Path('.')
    queriespath = repopath / 'queries'
    queriespath.mkdir(exist_ok=True)
    queryMap = dict() # Take it from server config
    for query in queries:
        basicquery = ns(query)
        step("Exporting query: {id} - {name}", **query)
        query = ns(redash.query(query['id']))

        slug = slugify(query.name)
        queryMap[query.id] = slug

        querypath = queriespath / slug
        querypath.mkdir(exist_ok=True)
        del query.user
        del query.last_modified_by
        query_text = query.pop('query')
        (querypath/'query.sql').write_text(query_text, encoding='utf8')
        visualizations = query.pop('visualizations',[])
        query.dump(querypath/'metadata.yaml')

        basicquery.dump(querypath/'basic.yaml')
        for vis in visualizations:
            vis = ns(vis)
            step("Exporting visualization {id} {type} {name}", **vis)
            viewslug = slugify(vis.name)
            vis.dump(querypath/'vis-{}.yaml'.format(viewslug))



    
    


if __name__=='__main__':
    cli()

